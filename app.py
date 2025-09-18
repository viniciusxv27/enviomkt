import datetime
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
import requests
from dotenv import load_dotenv
import base64
import mysql.connector
from mysql.connector import Error
import time
from minio import Minio
from minio.error import S3Error
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
logado = False
load_dotenv()

# Configuração do MinIO
def get_minio_client():
    """Retorna cliente do MinIO configurado"""
    try:
        endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        secure = os.getenv('MINIO_SECURE', 'False').lower() == 'true'
        
        # Remover protocolo se presente no endpoint
        if endpoint.startswith('https://'):
            endpoint = endpoint.replace('https://', '')
            secure = True  # Se URL tem https, forçar secure=True
        elif endpoint.startswith('http://'):
            endpoint = endpoint.replace('http://', '')
            secure = False  # Se URL tem http, forçar secure=False
        
        print(f"Conectando MinIO: endpoint={endpoint}, secure={secure}")
        
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        # Testar conexão
        client.list_buckets()
        print("Conexão com MinIO estabelecida com sucesso")
        
        return client
    except Exception as e:
        print(f"Erro ao configurar MinIO: {e}")
        return None

def ensure_bucket_exists():
    """Garante que o bucket existe"""
    try:
        client = get_minio_client()
        if not client:
            return False
        
        bucket_name = os.getenv('MINIO_BUCKET_NAME', 'disparo')
        print(f"Verificando bucket: {bucket_name}")
        
        # Verificar se bucket existe, se não, criar
        if not client.bucket_exists(bucket_name):
            print(f"Bucket '{bucket_name}' não existe, criando...")
            client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' criado com sucesso")
        else:
            print(f"Bucket '{bucket_name}' já existe")
        
        return True
    except Exception as e:
        print(f"Erro ao verificar/criar bucket: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_minio_connection():
    """Testa a conexão com MinIO"""
    try:
        print("=== TESTE DE CONEXÃO MINIO ===")
        client = get_minio_client()
        if not client:
            print("❌ Falha ao criar cliente MinIO")
            return False
        
        print("✅ Cliente MinIO criado")
        
        # Listar buckets para testar conexão
        buckets = client.list_buckets()
        print(f"✅ Conexão testada - buckets encontrados: {len(buckets)}")
        for bucket in buckets:
            print(f"  - {bucket.name}")
        
        # Testar bucket específico
        bucket_name = os.getenv('MINIO_BUCKET_NAME', 'disparo')
        if client.bucket_exists(bucket_name):
            print(f"✅ Bucket '{bucket_name}' existe")
        else:
            print(f"⚠️  Bucket '{bucket_name}' não existe")
        
        return True
    except Exception as e:
        print(f"❌ Erro no teste de conexão: {e}")
        import traceback
        traceback.print_exc()
        return False

def upload_video_to_minio(video_path, original_filename):
    """Faz upload do vídeo para o MinIO e retorna a URL"""
    try:
        print(f"Iniciando upload do vídeo: {original_filename}")
        
        client = get_minio_client()
        if not client:
            raise Exception("Erro ao conectar com MinIO")
        
        bucket_name = os.getenv('MINIO_BUCKET_NAME', 'disparo')
        print(f"Usando bucket: {bucket_name}")
        
        # Garantir que bucket existe
        print("Verificando se bucket existe...")
        if not ensure_bucket_exists():
            raise Exception("Erro ao garantir existência do bucket")
        
        # Gerar nome único para o arquivo
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"videos/{uuid.uuid4()}{file_extension}"
        print(f"Nome único gerado: {unique_filename}")
        
        # Upload do arquivo
        print(f"Fazendo upload do arquivo: {video_path}")
        client.fput_object(bucket_name, unique_filename, video_path)
        print("Upload concluído com sucesso")
        
        # Gerar URL pública (presigned URL com validade longa)
        print("Gerando URL presigned...")
        video_url = client.presigned_get_object(bucket_name, unique_filename, expires=datetime.timedelta(days=7))
        
        print(f"Vídeo enviado para MinIO: {unique_filename}")
        print(f"URL gerada: {video_url}")
        
        return video_url
        
    except S3Error as e:
        print(f"Erro S3 ao fazer upload: {e}")
        print(f"Código S3: {e.code if hasattr(e, 'code') else 'N/A'}")
        print(f"Mensagem S3: {e.message if hasattr(e, 'message') else 'N/A'}")
        raise Exception(f"Erro S3: {str(e)}")
    except Exception as e:
        print(f"Erro ao fazer upload para MinIO: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Erro MinIO: {str(e)}")

# Funções Evolution API
def get_evolution_api_headers():
    """Retorna os headers para requisições à Evolution API"""
    return {
        'Content-Type': 'application/json',
        'apikey': os.getenv('EVOLUTION_API_KEY', '')
    }

def create_evolution_instance(instance_name):
    """Cria uma nova instância na Evolution API"""
    try:
        url = f"{os.getenv('EVOLUTION_BASE_URL', '')}/instance/create"
        headers = get_evolution_api_headers()
        
        payload = {
            "instanceName": instance_name,
            "token": os.getenv('EVOLUTION_API_KEY', ''),
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
            "groupsIgnore": True,
            "webhook": {
                "url": "https://rede-confianca-n8n.lpl0df.easypanel.host/webhook/envia-msg-envio",
                "byEvents": True,
                "base64": True,
                "events": ["MESSAGES_UPSERT"],
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 201
    except Exception as e:
        print(f"Erro ao criar instância Evolution: {e}")
        return False

def connect_evolution_instance(instance_name):
    """Conecta uma instância na Evolution API"""
    try:
        url = f"{os.getenv('EVOLUTION_BASE_URL', '')}/instance/connect/{instance_name}"
        headers = get_evolution_api_headers()
        
        response = requests.get(url, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao conectar instância Evolution: {e}")
        return False

def get_qrcode_evolution(instance_name):
    """Busca o QR Code de uma instância na Evolution API"""
    try:
        # Primeiro tenta o endpoint de conexão
        url = f"{os.getenv('EVOLUTION_BASE_URL', '')}/instance/connect/{instance_name}"
        headers = get_evolution_api_headers()
        
        print(f"Buscando QR Code para instância: {instance_name}")
        print(f"URL: {url}")
        print(f"Headers: {headers}")
        
        response = requests.get(url, headers=headers)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {data}")
            
            # O QR Code pode vir em diferentes formatos dependendo da Evolution API
            if 'qrcode' in data:
                qr_data = data['qrcode']
                print(f"QR Code encontrado no campo 'qrcode'")
                return qr_data.replace('data:image/png;base64,', '') if qr_data.startswith('data:') else qr_data
            elif 'base64' in data:
                qr_data = data['base64']
                print(f"QR Code encontrado no campo 'base64'")
                return qr_data.replace('data:image/png;base64,', '') if qr_data.startswith('data:') else qr_data
            elif 'qr' in data:
                qr_data = data['qr']
                print(f"QR Code encontrado no campo 'qr'")
                return qr_data.replace('data:image/png;base64,', '') if qr_data.startswith('data:') else qr_data
            else:
                print(f"Campos disponíveis na resposta: {list(data.keys())}")
        else:
            print(f"Erro na requisição: {response.status_code} - {response.text}")
        
        # Se não conseguir pelo endpoint de connect, tenta buscar instância específica
        url2 = f"{os.getenv('EVOLUTION_BASE_URL', '')}/instance/{instance_name}"
        response2 = requests.get(url2, headers=headers)
        print(f"Tentando URL alternativa: {url2}")
        print(f"Response status 2: {response2.status_code}")
        
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"Response data 2: {data2}")
            if 'qrcode' in data2:
                return data2['qrcode'].replace('data:image/png;base64,', '') if data2['qrcode'].startswith('data:') else data2['qrcode']
        
        return None
    except Exception as e:
        print(f"Erro ao buscar QR Code: {e}")
        return None

def get_instance_status(instance_name):
    """Verifica o status de uma instância na Evolution API"""
    try:
        # Primeiro tenta buscar instância específica
        url = f"{os.getenv('EVOLUTION_BASE_URL', '')}/instance/fetchInstances"
        headers = get_evolution_api_headers()
        
        print(f"Verificando status da instância: {instance_name}")
        print(f"URL: {url}")
        
        response = requests.get(url, headers=headers)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            instances = response.json()
            print(f"Instâncias encontradas: {len(instances) if isinstance(instances, list) else 'Não é lista'}")
            
            # Se a resposta é uma lista
            if isinstance(instances, list):
                for instance in instances:
                    if isinstance(instance, dict):
                        # Verifica diferentes estruturas possíveis
                        instance_data = instance.get('instance', instance)
                        if instance_data.get('instanceName') == instance_name or instance_data.get('name') == instance_name:
                            status = instance_data.get('state', instance_data.get('connectionStatus', 'close'))
                            print(f"Status encontrado: {status}")
                            return status
            
            # Se a resposta é um objeto
            elif isinstance(instances, dict):
                for key, instance in instances.items():
                    if isinstance(instance, dict):
                        if instance.get('instanceName') == instance_name or instance.get('name') == instance_name:
                            status = instance.get('state', instance.get('connectionStatus', 'close'))
                            print(f"Status encontrado: {status}")
                            return status
        
        # Tenta endpoint alternativo
        url2 = f"{os.getenv('EVOLUTION_BASE_URL', '')}/instance/{instance_name}"
        response2 = requests.get(url2, headers=headers)
        print(f"Tentando URL alternativa: {url2}")
        print(f"Response status 2: {response2.status_code}")
        
        if response2.status_code == 200:
            data = response2.json()
            if isinstance(data, dict):
                status = data.get('state', data.get('connectionStatus', 'close'))
                print(f"Status alternativo: {status}")
                return status
        
        print("Status não encontrado, retornando 'close'")
        return 'close'
        
    except Exception as e:
        print(f"Erro ao buscar status da instância: {e}")
        return 'close'

def get_contacts_from_instance(instance_name):
    """Busca todos os contatos/chats de uma instância via Evolution API"""
    contacts = []
    base_url = os.getenv('EVOLUTION_BASE_URL', '')
    headers = get_evolution_api_headers()
    try:
        # Tentar primeiro o endpoint padrão
        url = f"{base_url}/chat/findContacts/{instance_name}"
        print(f"🔍 Buscando chats para instância: {instance_name}")
        print(f"🔗 URL: {url}")
        
        response = requests.post(url, headers=headers, timeout=15)
        print(f"📊 Status da resposta: {response.status_code}")
        
        # Se falhou, tentar endpoint alternativo
        if response.status_code != 200:
            print("⚠️ Tentando endpoint alternativo...")
            url_alt = f"{base_url}/chat/findChats/{instance_name}"
            print(f"🔗 URL alternativa: {url_alt}")
            response = requests.post(url_alt, headers=headers, timeout=15)
            print(f"📊 Status da resposta alternativa: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📋 Dados recebidos: tipo={type(data)}, tamanho={len(data) if isinstance(data, (list, dict)) else 'N/A'}")
            
            chats = data if isinstance(data, list) else data.get('data', [])
            print(f"💬 Chats encontrados: {len(chats)}")
            
            for i, chat in enumerate(chats):
                if i < 3:  # Log apenas os primeiros 3 para debug
                    print(f"📱 Chat {i+1}: {chat}")
                
                remote_jid = chat.get('remoteJid') or chat.get('id')
                print(f"🆔 RemoteJid encontrado: {remote_jid}")
                
                if remote_jid and not remote_jid.endswith('@g.us'):
                    # Formatar timestamp
                    formatted_time = chat.get('updatedAt', '')
                    if formatted_time and 'T' in formatted_time:
                        try:
                            # Parse ISO format: 2025-08-12T10:03:11.000Z
                            dt = datetime.datetime.fromisoformat(formatted_time.replace('Z', '+00:00'))
                            formatted_time = dt.strftime('%d/%m/%Y %H:%M')
                        except:
                            formatted_time = 'Data inválida'
                    
                    contact = {
                        'remoteJid': remote_jid,
                        'profilePicUrl': chat.get('profilePicUrl', ''),
                        'name': chat.get('pushName') or remote_jid.split('@')[0],
                        'pushName': chat.get('pushName', ''),
                        'formatted_time': formatted_time
                    }
                    contacts.append(contact)
                    print(f"✅ Contato adicionado: {contact['name']} ({remote_jid})")
                else:
                    print(f"⏭️ Ignorando chat (grupo ou inválido): {remote_jid}")
        else:
            print(f"❌ Erro ao buscar contatos na Evolution API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro ao buscar contatos na Evolution API: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"📊 Total de contatos retornados: {len(contacts)}")
    return contacts

def get_messages_from_chat(instance_name, remote_jid):
    """Busca mensagens de um chat específico via Evolution API"""
    base_url = os.getenv('EVOLUTION_BASE_URL', '')
    headers = get_evolution_api_headers()
    messages = []
    try:
        url = f"{base_url}/chat/findMessages/{instance_name}"
        payload = {
            "where": {
                "key" : {
                    "remoteJid": remote_jid
                }
            }
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            msgs = data if isinstance(data, list) else data.get('data', [])
            for msg in msgs:
                # Formatar timestamp
                if msg.get('messageTimestamp'):
                    import datetime
                    try:
                        msg['formatted_time'] = datetime.datetime.fromtimestamp(
                            int(msg['messageTimestamp']) / 1000
                        ).strftime('%d/%m/%Y %H:%M')
                    except:
                        msg['formatted_time'] = 'Data inválida'
                else:
                    msg['formatted_time'] = 'Sem data'
                messages.append(msg)
        else:
            print(f"❌ Erro ao buscar mensagens na Evolution API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens na Evolution API: {e}")
    return messages

def update_whatsapp_number_description(numero_id, new_description, link_planilha=None):
    """Atualiza a descrição e link da planilha de um número do WhatsApp"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        if link_planilha is not None:
            query = "UPDATE numeros SET descricao = %s, link_planilha = %s WHERE id = %s"
            cursor.execute(query, (new_description, link_planilha, numero_id))
        else:
            query = "UPDATE numeros SET descricao = %s WHERE id = %s"
            cursor.execute(query, (new_description, numero_id))
        connection.commit()
        return True
    except Error as e:
        print(f"Erro ao atualizar descrição: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def delete_whatsapp_number(numero_id):
    """Remove um número do WhatsApp do banco de dados"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        query = "DELETE FROM numeros WHERE id = %s"
        cursor.execute(query, (numero_id,))
        connection.commit()
        return cursor.rowcount > 0  # Retorna True se algum registro foi deletado
    except Error as e:
        print(f"Erro ao remover número: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Configuração do banco de dados
def get_db_connection():
    """Conexão com o banco principal do sistema"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'whatsapp'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            #port=int(os.getenv('DB_PORT', 3306))
        )
        return connection
    except Error as e:
        print(f"Erro ao conectar ao MySQL (sistema): {e}")
        return None

def get_evolution_db_connection():
    """Conexão com o banco da Evolution API"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('EVOLUTION_DB_HOST', 'localhost'),
            database=os.getenv('EVOLUTION_DB_NAME', 'evolution'),
            user=os.getenv('EVOLUTION_DB_USER', 'root'),
            password=os.getenv('EVOLUTION_DB_PASSWORD', ''),
            #port=int(os.getenv('EVOLUTION_DB_PORT', 3306))
        )
        return connection
    except Error as e:
        print(f"Erro ao conectar ao MySQL (Evolution): {e}")
        return None

def get_whatsapp_numbers():
    """Busca todos os números do WhatsApp cadastrados com status da Evolution"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        # Buscar dados da tabela numeros do sistema principal
        query = "SELECT * FROM numeros ORDER BY id"
        cursor.execute(query)
        numbers = cursor.fetchall()
        
        print(f"Números encontrados no banco principal: {len(numbers)}")
        
        # Para cada número, verificar status na Evolution API via HTTP
        for number in numbers:
            try:
                # Verificar status via API da Evolution (mais confiável)
                status = get_instance_status(number['instancia'])
                
                if status in ['open', 'connected']:
                    number['status'] = 'Conectado'
                    number['status_class'] = 'connected'
                elif status == 'connecting':
                    number['status'] = 'Conectando'
                    number['status_class'] = 'connecting'
                else:
                    number['status'] = 'Desconectado'
                    number['status_class'] = 'disconnected'
                    
            except Exception as e:
                print(f"Erro ao verificar status da instância {number['instancia']}: {e}")
                number['status'] = 'Desconectado'
                number['status_class'] = 'disconnected'
        
        return numbers
        
    except Error as e:
        print(f"Erro ao buscar números: {e}")
        return []
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def create_whatsapp_number(numero, remotejid, descricao, instancia, link_planilha=None):
    """Cria um novo número do WhatsApp"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        # Usar a tabela correta: numeros
        query = "INSERT INTO numeros (numero, remotejid, descricao, instancia, link_planilha) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (numero, remotejid, descricao, instancia, link_planilha))
        connection.commit()
        return True
    except Error as e:
        print(f"Erro ao criar número: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Aqui você pode adicionar lógica de autenticação
        
        if username == str(os.getenv("USERNAME")) and password == str(os.getenv("PASSWORD")):
            global logado
            logado = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Credenciais inválidas')
    return render_template('login.html')

@app.route('/numeros/reconectar/<instancia>')
def reconectar_numero(instancia):
    """Rota para reconectar um número desconectado"""
    try:
        # Tentar conectar a instância na Evolution API
        connect_url = f"{os.getenv('EVOLUTION_BASE_URL', '')}/instance/connect/{instancia}"
        headers = get_evolution_api_headers()
        
        print(f"Tentando reconectar instância: {instancia}")
        print(f"URL: {connect_url}")
        
        # Primeiro tentar conectar
        connect_response = requests.get(connect_url, headers=headers, timeout=10)
        print(f"Response status: {connect_response.status_code}")
        print(f"Response text: {connect_response.text}")
        
        if connect_response.status_code in [200, 201]:
            print(f"Instância {instancia} conectada/reconectada com sucesso")
            
            # Aguardar um pouco e obter QR Code
            time.sleep(2)
            qr_code = get_qrcode_evolution(instancia)
            
            return render_template('criar_numero.html', 
                                 instancia=instancia, 
                                 show_qr=True,
                                 qr_code=qr_code,
                                 reconnect=True)
        else:
            error_msg = f"Erro ao reconectar: Status {connect_response.status_code}"
            try:
                error_data = connect_response.json()
                if 'message' in error_data:
                    error_msg = error_data['message']
            except:
                pass
            
            return render_template('numeros.html', 
                                 numbers=get_whatsapp_numbers(),
                                 error=error_msg)
            
    except Exception as e:
        print(f"Erro ao reconectar: {e}")
        return render_template('numeros.html', 
                             numbers=get_whatsapp_numbers(),
                             error=f"Erro ao reconectar: {str(e)}")

@app.route('/numeros')
def numeros():
    """Lista todos os números cadastrados"""
    if not logado:
        return redirect(url_for('login'))
    
    numbers = get_whatsapp_numbers()
    return render_template('numeros.html', numbers=numbers)

@app.route('/numeros/criar', methods=['GET', 'POST'])
def criar_numero():
    """Cria um novo número"""
    if not logado:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Se é uma requisição para criar a instância
        if 'create_instance' in request.form:
            instancia = request.form.get('instancia', '').strip()
            if instancia:
                # Criar instância na Evolution API
                if create_evolution_instance(instancia):
                    # Buscar QR Code
                    qr_code = get_qrcode_evolution(instancia)
                    return render_template('criar_numero.html', 
                                         instancia=instancia, 
                                         qr_code=qr_code,
                                         show_qr=True)
                else:
                    return render_template('criar_numero.html', 
                                         error='Erro ao criar instância na Evolution API')
        
        # Se é uma requisição para salvar o número
        elif 'save_number' in request.form:
            numero = request.form.get('numero', '').strip()
            remotejid = request.form.get('remotejid', '').strip()
            descricao = request.form.get('descricao', '').strip()
            instancia = request.form.get('instancia', '').strip()
            link_planilha = request.form.get('link_planilha', '').strip()
            
            if not all([numero, remotejid, descricao, instancia]):
                return render_template('criar_numero.html', error='Todos os campos são obrigatórios')
            
            # Verificar se a instância está conectada
            status = get_instance_status(instancia)
            if status != 'open':
                qr_code = get_qrcode_evolution(instancia)
                return render_template('criar_numero.html', 
                                     instancia=instancia,
                                     qr_code=qr_code,
                                     show_qr=True,
                                     error='WhatsApp ainda não está conectado. Escaneie o QR Code.')
            
            # Salvar o número no banco
            if create_whatsapp_number(numero, remotejid, descricao, instancia, link_planilha):
                return redirect(url_for('numeros'))
            else:
                return render_template('criar_numero.html', error='Erro ao criar número')
    
    return render_template('criar_numero.html')

@app.route('/api/instance-status/<string:instance_name>')
def check_instance_status(instance_name):
    """API para verificar status da instância"""
    if not logado:
        return {'status': 'error', 'message': 'Não autorizado'}, 401
    
    try:
        status = get_instance_status(instance_name)
        qr_code = None
        
        print(f"Status da instância {instance_name}: {status}")
        
        # Se não está conectado, tentar buscar QR Code
        if status not in ['open', 'connected']:
            qr_code = get_qrcode_evolution(instance_name)
            print(f"QR Code obtido: {'Sim' if qr_code else 'Não'}")
        
        # Mapear status para valores mais claros
        connected = status in ['open', 'connected']
        
        return {
            'status': status, 
            'connected': connected,
            'qr_code': qr_code,
            'timestamp': int(time.time()) if 'time' in globals() else None
        }
    except Exception as e:
        print(f"Erro na API de status: {e}")
        return {
            'status': 'error',
            'connected': False,
            'error': str(e)
        }, 500

@app.route('/debug/qr/<string:instance_name>')
def debug_qr(instance_name):
    """Debug para QR Code"""
    if not logado:
        return redirect(url_for('login'))
    
    qr_code = get_qrcode_evolution(instance_name)
    status = get_instance_status(instance_name)
    
    return {
        'instance': instance_name,
        'qr_code': qr_code,
        'status': status,
        'has_qr': qr_code is not None,
        'qr_length': len(qr_code) if qr_code else 0
    }

@app.route('/debug/minio')
def debug_minio():
    """Debug para conexão MinIO"""
    if not logado:
        return redirect(url_for('login'))
    
    try:
        result = test_minio_connection()
        return {
            'status': 'success' if result else 'error',
            'connection_test': result,
            'endpoint': os.getenv('MINIO_ENDPOINT'),
            'bucket': os.getenv('MINIO_BUCKET_NAME'),
            'secure': os.getenv('MINIO_SECURE')
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'endpoint': os.getenv('MINIO_ENDPOINT'),
            'bucket': os.getenv('MINIO_BUCKET_NAME'),
            'secure': os.getenv('MINIO_SECURE')
        }, 500

@app.route('/numeros/editar/<int:numero_id>', methods=['GET', 'POST'])
def editar_numero(numero_id):
    """Edita a descrição de um número"""
    if not logado:
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('numeros'))
    
    if request.method == 'POST':
        nova_descricao = request.form.get('descricao', '').strip()
        link_planilha = request.form.get('link_planilha', '').strip()
        if nova_descricao:
            if update_whatsapp_number_description(numero_id, nova_descricao, link_planilha):
                return redirect(url_for('numeros'))
    
    # Buscar dados do número
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM numeros WHERE id = %s"
        cursor.execute(query, (numero_id,))
        numero = cursor.fetchone()
        
        if not numero:
            return redirect(url_for('numeros'))
        
        return render_template('editar_numero.html', numero=numero)
    except Error as e:
        print(f"Erro ao buscar número: {e}")
        return redirect(url_for('numeros'))
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/numeros/remover/<int:numero_id>', methods=['POST'])
def remover_numero(numero_id):
    """Remove um número do WhatsApp"""
    if not logado:
        return redirect(url_for('login'))
    
    try:
        if delete_whatsapp_number(numero_id):
            return redirect(url_for('numeros'))
        else:
            # Se não conseguiu remover, volta para a lista com erro
            numbers = get_whatsapp_numbers()
            return render_template('numeros.html', 
                                 numbers=numbers, 
                                 error='Erro ao remover o número. Verifique se ele existe.')
    except Exception as e:
        print(f"Erro ao remover número: {e}")
        numbers = get_whatsapp_numbers()
        return render_template('numeros.html', 
                             numbers=numbers, 
                             error=f'Erro ao remover número: {str(e)}')

@app.route('/chats/<string:instancia>')
def visualizar_chats(instancia):
    """Visualiza todos os chats de uma instância"""
    if not logado:
        return redirect(url_for('login'))
    
    # Buscar todos os contatos/chats da instância
    contacts = get_contacts_from_instance(instancia)
    remote_jid = request.args.get('remoteJid')
    messages = []
    contact_info = None
    if remote_jid:
        messages, contact_info = get_messages_and_info(instancia, remote_jid)
    return render_template('chats.html', 
                         contacts=contacts,
                         instancia=instancia,
                         selected_jid=remote_jid,
                         messages=messages,
                         contact_info=contact_info)

def get_messages_and_info(instance_name, remote_jid, limit=50):
    """Busca mensagens e info do contato via Evolution API"""
    base_url = os.getenv('EVOLUTION_BASE_URL', '')
    headers = get_evolution_api_headers()
    messages = []
    contact_info = None
    try:
        url = f"{base_url}/chat/findMessages/{instance_name}"
        payload = {
            "where": {
                "key": {
                    "remoteJid": remote_jid
                }
            },
            "limit": limit
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            records = data.get('messages', {}).get('records', [])
            for msg in records:
                # Formatar timestamp e subtrair 3 horas
                if msg.get('messageTimestamp'):
                    import datetime
                    try:
                        dt = datetime.datetime.fromtimestamp(int(msg['messageTimestamp'])) - datetime.timedelta(hours=3)
                        msg['formatted_time'] = dt.strftime('%d/%m/%Y %H:%M')
                    except:
                        msg['formatted_time'] = 'Data inválida'
                else:
                    msg['formatted_time'] = 'Sem data'
                messages.append(msg)
            # Info do contato
            if records and 'key' in records[0]:
                contact_info = {
                    'remoteJid': records[0]['key']['remoteJid'],
                    'fromMe': records[0]['key'].get('fromMe', False),
                    'pushName': records[0].get('pushName', '')
                }
        else:
            print(f"❌ Erro ao buscar mensagens na Evolution API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens na Evolution API: {e}")
    return messages, contact_info

@app.route('/mensagens/<string:instancia>/<string:remote_jid>')
def visualizar_mensagens(instancia, remote_jid):
    """Visualiza mensagens de uma conversa"""
    if not logado:
        return redirect(url_for('login'))
    
    messages = get_messages_from_chat(instancia, remote_jid)
    
    # Buscar informações do contato
    connection = get_evolution_db_connection()
    contact_info = {}
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT name, pushName FROM Contact WHERE remoteJid = %s AND instance = %s LIMIT 1"
            cursor.execute(query, (remote_jid, instancia))
            result = cursor.fetchone()
            if result:
                contact_info = result
        except Error as e:
            print(f"Erro ao buscar contato: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    return render_template('mensagens.html', 
                         messages=messages, 
                         contact_info=contact_info,
                         remote_jid=remote_jid,
                         instancia=instancia)

@app.route('/', methods=['GET', 'POST'])
def index():# Verifica se o usuário está autenticado
    if not logado:
        return redirect(url_for('login'))

    # Buscar números disponíveis para o select
    numbers = get_whatsapp_numbers()

    if request.method == 'POST':
        # Verificar se todos os campos obrigatórios estão presentes
        if 'excel_file' not in request.files:
            return render_template('index.html', error='Arquivo Excel é obrigatório', numbers=numbers)
        
        file = request.files['excel_file']
        if file.filename == '':
            return render_template('index.html', error='Nenhum arquivo Excel foi selecionado', numbers=numbers)
            
        message = request.form.get('message', '').strip()
        message2 = request.form.get('message2', '').strip()
        message3 = request.form.get('message3', '').strip()
        
        if not message:
            return render_template('index.html', error='Mensagem principal é obrigatória', numbers=numbers)

        instancia = request.form.get('whatsapp_number', '').strip()
        if not instancia:
            return render_template('index.html', error='Selecione um número do WhatsApp', numbers=numbers)
            
        # Buscar link_planilha da instância selecionada
        link_planilha = None
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor(dictionary=True)
                query = "SELECT link_planilha FROM numeros WHERE instancia = %s LIMIT 1"
                cursor.execute(query, (instancia,))
                result = cursor.fetchone()
                if result:
                    link_planilha = result.get('link_planilha')
            except Error as e:
                print(f"Erro ao buscar link_planilha: {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
            
        data_agendamento = request.form.get('schedule_date') if request.form.get('schedule_date') else None
        horario_agendamento = request.form.get('schedule_time') if request.form.get('schedule_time') else None
        haImg = False
        haVideo = False
        leads = []

        # Processar imagem se fornecida
        image_base64 = None
        if 'image_file' in request.files and request.files['image_file'] and request.files['image_file'].filename:
            haImg = True
            image_file = request.files['image_file']
            print(f"Arquivo de imagem detectado: {image_file.filename}")
            
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
            image_file.save(image_path)
            with open(image_path, "rb") as img_file:
                image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                print(f"Imagem convertida para base64, tamanho: {len(image_base64)} caracteres")

        # Processar vídeo se fornecida
        video_url = None
        if 'video_file' in request.files and request.files['video_file'] and request.files['video_file'].filename:
            video_file = request.files['video_file']
            print(f"Arquivo de vídeo detectado: {video_file.filename}")
            
            # Verificar se é MP4
            if not video_file.filename.lower().endswith('.mp4'):
                print("Erro: Arquivo não é MP4")
                return render_template('index.html', error='Apenas arquivos MP4 são permitidos para vídeo', numbers=numbers)
            
            try:
                haVideo = True
                video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file.filename)
                video_file.save(video_path)
                print(f"Vídeo salvo temporariamente em: {video_path}")
                
                # Verificar tamanho do arquivo
                video_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                print(f"Tamanho do vídeo: {video_size_mb:.2f} MB")
                
                # Verificar se o vídeo não é muito grande (limite de 100MB para MinIO)
                if video_size_mb > 100:
                    os.remove(video_path)  # Limpar arquivo temporário
                    print("Erro: Vídeo muito grande")
                    return render_template('index.html', error=f'Vídeo muito grande ({video_size_mb:.1f}MB). Máximo permitido: 100MB', numbers=numbers)
                
                # Upload para MinIO
                video_url = upload_video_to_minio(video_path, video_file.filename)
                print(f"Vídeo enviado para MinIO com sucesso")
                
                # Remover arquivo temporário
                os.remove(video_path)
                print(f"Arquivo temporário removido: {video_path}")
                
            except Exception as e:
                print(f"Erro ao processar vídeo: {e}")
                return render_template('index.html', error=f'Erro ao processar vídeo: {str(e)}', numbers=numbers)

        try:
            if file and file.filename.endswith('.xlsx'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                df = pd.read_excel(filepath)
                data_list = df.to_dict(orient='records')

                print("Mensagem principal:", message)
                print("Mensagem 2:", message2 if message2 else "Não informada")
                print("Mensagem 3:", message3 if message3 else "Não informada")
                print("Número WhatsApp selecionado:", instancia)
                print("Data agendamento:", data_agendamento)
                print("Horário agendamento:", horario_agendamento)
                print("Tem imagem:", haImg)
                print("Tem vídeo:", haVideo)
                print("Dados importados:")
                for row in data_list:
                    filial = row.get('Filial')
                    data = row.get('Data')
                    nome = row.get('Nome Cliente')
                    plano = row.get('Plano')
                    telefone = row.get('Acesso')
                    complemento = row.get('Complemento')

                    leads.append({
                        'filial': str(filial) if filial else '',
                        'data': str(data) if data else '',
                        'nome': str(nome) if nome else '',
                        'plano': str(plano) if plano else '',
                        'telefone': str(telefone) if telefone else '',
                        'complemento': str(complemento) if complemento else ''
                    })

                payload = {
                    'message': message,
                    'message2': message2 if message2 else message,
                    'message3': message3 if message3 else message,
                    'leads': leads,
                    'haImg': haImg,
                    'base64': image_base64 if haImg else None,
                    'haVideo': haVideo,
                    'video_url': video_url if haVideo else None,
                    'data_agendamento': data_agendamento,
                    'horario_agendamento': horario_agendamento,
                    'instancia': instancia,
                    'link_planilha': link_planilha
                }

                # Log do payload sem os base64 (que são muito grandes)
                payload_debug = {
                    'message': message,
                    'message2': message2 if message2 else None,
                    'message3': message3 if message3 else None,
                    'leads_count': len(leads),
                    'haImg': haImg,
                    'base64_size': len(image_base64) if image_base64 else 0,
                    'haVideo': haVideo,
                    'video_url': video_url if video_url else None,
                    'data_agendamento': data_agendamento,
                    'horario_agendamento': horario_agendamento,
                    'instancia': instancia,
                    'link_planilha': link_planilha
                }
                print("Payload debug:", payload_debug)
                
                # Usar timeout maior para vídeos
                timeout_seconds = 300 if haVideo else 60  # 5 minutos para vídeo, 1 minuto para outros
                print(f"Enviando para webhook com timeout de {timeout_seconds} segundos...")
                
                try:
                    response = requests.post('https://rede-confianca-n8n.lpl0df.easypanel.host/webhook/disparo-rede-confianca', 
                                           json=payload, 
                                           timeout=timeout_seconds)
                    print("Resposta do webhook:", response.status_code, response.text)
                    return render_template('index.html', success=True, data=payload_debug, numbers=numbers)
                except requests.exceptions.Timeout:
                    print("Erro: Timeout na requisição do webhook")
                    return render_template('index.html', error='Timeout ao enviar dados para o webhook. Tente com um vídeo menor.', numbers=numbers)
                except requests.exceptions.RequestException as e:
                    print(f"Erro na requisição do webhook: {e}")
                    return render_template('index.html', error=f'Erro ao enviar dados para o webhook: {str(e)}', numbers=numbers)
            else:
                return render_template('index.html', error='Por favor, selecione um arquivo Excel válido (.xlsx)', numbers=numbers)
            
        except Exception as e:
            print(f"Erro durante o processamento: {str(e)}")
            return render_template('index.html', error=f'Erro ao processar arquivo: {str(e)}', numbers=numbers)
    
    return render_template('index.html', success=False, numbers=numbers)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
    #app.run(host="0.0.0.0", port=5001, debug=True)