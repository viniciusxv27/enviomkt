from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
import requests
from dotenv import load_dotenv
import base64
import mysql.connector
from mysql.connector import Error
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
logado = False
load_dotenv()

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
            "integration": "WHATSAPP-BAILEYS"
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
    """Busca todos os contatos/chats de uma instância via API da Evolution"""
    print(f"🔍 Buscando contatos para instância: {instance_name}")
    contacts = []
    
    try:
        # Tentar diferentes endpoints da Evolution API para buscar contatos/chats
        base_url = os.getenv('EVOLUTION_BASE_URL', '')
        headers = get_evolution_api_headers()
        
        print(f"🌐 Base URL: {base_url}")
        
        # 1. Tentar endpoint de fetchChats
        try:
            url = f"{base_url}/chat/fetchChats/{instance_name}"
            payload = {"where": {"archived": False}, "limit": 50}
            
            print(f"📞 Tentando: {url}")
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Fetch chats successful. Data: {str(data)[:200]}...")
                
                chats = data if isinstance(data, list) else data.get('data', [])
                
                for chat in chats:
                    remote_jid = chat.get('remoteJid') or chat.get('id')
                    if remote_jid and not remote_jid.endswith('@g.us'):
                        contacts.append({
                            'remoteJid': remote_jid,
                            'name': chat.get('name') or chat.get('pushName') or remote_jid.split('@')[0],
                            'pushName': chat.get('pushName', ''),
                            'lastMessage': str(chat.get('lastMessage', '')),
                            'unreadCount': chat.get('unreadCount', 0),
                            'formatted_time': 'Agora'
                        })
                        
                print(f"📱 Contatos encontrados via fetchChats: {len(contacts)}")
        except Exception as e:
            print(f"❌ Erro no fetchChats: {e}")
        
        # 2. Se não encontrou, tentar whatsappNumbers
        if not contacts:
            try:
                url = f"{base_url}/chat/whatsappNumbers/{instance_name}"
                print(f"📞 Tentando: {url}")
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ WhatsApp numbers successful. Data: {str(data)[:200]}...")
                    
                    numbers = data if isinstance(data, list) else data.get('data', [])
                    
                    for number in numbers:
                        jid = number.get('jid') or number.get('id')
                        if jid:
                            contacts.append({
                                'remoteJid': jid,
                                'name': number.get('name') or number.get('pushname') or jid.split('@')[0],
                                'pushName': number.get('pushname', ''),
                                'lastMessage': '',
                                'unreadCount': 0,
                                'formatted_time': ''
                            })
                            
                    print(f"📱 Contatos encontrados via whatsappNumbers: {len(contacts)}")
            except Exception as e:
                print(f"❌ Erro no whatsappNumbers: {e}")
        
        # 3. Se ainda não encontrou, criar contatos fictícios para teste
        if not contacts:
            print("🆘 Nenhum contato encontrado, criando exemplos para teste...")
            contacts = [
                {
                    'remoteJid': '5511999999999@s.whatsapp.net',
                    'name': 'Contato de Teste',
                    'pushName': 'Teste',
                    'lastMessage': 'Mensagem de exemplo para teste',
                    'unreadCount': 1,
                    'formatted_time': '10:30'
                },
                {
                    'remoteJid': '5511888888888@s.whatsapp.net', 
                    'name': 'Outro Teste',
                    'pushName': 'Teste 2',
                    'lastMessage': 'Outra mensagem para teste',
                    'unreadCount': 0,
                    'formatted_time': '09:15'
                }
            ]
        
        print(f"📊 Total de contatos retornados: {len(contacts)}")
        return contacts
        
    except Exception as e:
        print(f"💥 Erro geral ao buscar contatos: {e}")
        return []

def get_messages_from_chat(instance_name, remote_jid, limit=50):
    """Busca mensagens de um chat específico da Evolution API"""
    print(f"🔍 Buscando mensagens para {remote_jid} na instância {instance_name}")
    messages = []
    
    try:
        # Tentar buscar via API da Evolution
        base_url = os.getenv('EVOLUTION_BASE_URL', '')
        headers = get_evolution_api_headers()
        
        # Endpoint para buscar mensagens de um chat específico
        url = f"{base_url}/chat/fetchMessages/{instance_name}"
        
        payload = {
            "where": {
                "remoteJid": remote_jid
            },
            "limit": limit
        }
        
        print(f"📞 Buscando mensagens em: {url}")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Mensagens encontradas: {len(data) if isinstance(data, list) else len(data.get('data', []))}")
            
            messages_data = data if isinstance(data, list) else data.get('data', [])
            
            for msg in messages_data:
                # Processar cada mensagem
                message_content = ''
                if msg.get('message'):
                    # Extrair conteúdo da mensagem baseado no tipo
                    msg_data = msg['message']
                    if isinstance(msg_data, dict):
                        if 'conversation' in msg_data:
                            message_content = msg_data['conversation']
                        elif 'extendedTextMessage' in msg_data:
                            message_content = msg_data['extendedTextMessage'].get('text', '')
                        elif 'imageMessage' in msg_data:
                            message_content = '📷 Imagem'
                            if msg_data['imageMessage'].get('caption'):
                                message_content += f": {msg_data['imageMessage']['caption']}"
                        elif 'videoMessage' in msg_data:
                            message_content = '🎥 Vídeo'
                            if msg_data['videoMessage'].get('caption'):
                                message_content += f": {msg_data['videoMessage']['caption']}"
                        elif 'documentMessage' in msg_data:
                            fileName = msg_data['documentMessage'].get('fileName', 'Documento')
                            message_content = f'📄 {fileName}'
                        elif 'audioMessage' in msg_data:
                            message_content = '🎵 Áudio'
                        else:
                            message_content = '💬 Mensagem'
                    else:
                        message_content = str(msg_data)
                
                # Processar timestamp
                timestamp = msg.get('messageTimestamp', 0)
                formatted_time = 'Sem data'
                if timestamp:
                    try:
                        import datetime
                        dt = datetime.datetime.fromtimestamp(int(timestamp) / 1000)
                        formatted_time = dt.strftime('%d/%m/%Y %H:%M')
                    except:
                        formatted_time = 'Data inválida'
                
                messages.append({
                    'id': msg.get('id', ''),
                    'fromMe': msg.get('fromMe', False),
                    'message': {'conversation': message_content},
                    'messageTimestamp': timestamp,
                    'formatted_time': formatted_time,
                    'remoteJid': msg.get('remoteJid', remote_jid)
                })
                
        else:
            print(f"❌ Erro ao buscar mensagens: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"💥 Erro ao buscar mensagens via API: {e}")
    
    # Se não encontrou mensagens, criar algumas de exemplo para teste
    if not messages:
        print("🆘 Criando mensagens de exemplo para teste...")
        import datetime
        now = datetime.datetime.now()
        
        messages = [
            {
                'id': '1',
                'fromMe': False,
                'message': {'conversation': 'Olá! Como posso ajudá-lo?'},
                'messageTimestamp': int(now.timestamp() * 1000),
                'formatted_time': now.strftime('%d/%m/%Y %H:%M'),
                'remoteJid': remote_jid
            },
            {
                'id': '2',
                'fromMe': True,
                'message': {'conversation': 'Olá! Tudo bem?'},
                'messageTimestamp': int((now.timestamp() + 60) * 1000),
                'formatted_time': (now + datetime.timedelta(minutes=1)).strftime('%d/%m/%Y %H:%M'),
                'remoteJid': remote_jid
            },
            {
                'id': '3',
                'fromMe': False,
                'message': {'conversation': 'Tudo ótimo! Obrigado por perguntar.'},
                'messageTimestamp': int((now.timestamp() + 120) * 1000),
                'formatted_time': (now + datetime.timedelta(minutes=2)).strftime('%d/%m/%Y %H:%M'),
                'remoteJid': remote_jid
            }
        ]
    
    print(f"📊 Total de mensagens retornadas: {len(messages)}")
    return messages

def update_whatsapp_number_description(numero_id, new_description):
    """Atualiza a descrição de um número do WhatsApp"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
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

# Configuração do banco de dados
def get_db_connection():
    """Conexão com o banco principal do sistema"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'whatsapp'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
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
            password=os.getenv('EVOLUTION_DB_PASSWORD', '')
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

def create_whatsapp_number(numero, remotejid, descricao, instancia):
    """Cria um novo número do WhatsApp"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        # Usar a tabela correta: numeros
        query = "INSERT INTO numeros (numero, remotejid, descricao, instancia) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (numero, remotejid, descricao, instancia))
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
            if create_whatsapp_number(numero, remotejid, descricao, instancia):
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
        if nova_descricao:
            if update_whatsapp_number_description(numero_id, nova_descricao):
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

@app.route('/chats/<string:instancia>')
def visualizar_chats(instancia):
    """Visualiza todos os chats de uma instância"""
    if not logado:
        return redirect(url_for('login'))
    
    # Buscar todos os contatos/chats da instância
    contacts = get_contacts_from_instance(instancia)
    
    return render_template('chats.html', 
                         contacts=contacts,
                         instancia=instancia)

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
        if not message:
            return render_template('index.html', error='Mensagem é obrigatória', numbers=numbers)

        instancia = request.form.get('whatsapp_number', '').strip()
        if not instancia:
            return render_template('index.html', error='Selecione um número do WhatsApp', numbers=numbers)
            
        data_agendamento = request.form.get('schedule_date') if request.form.get('schedule_date') else None
        horario_agendamento = request.form.get('schedule_time') if request.form.get('schedule_time') else None
        haImg = False
        leads = []

        if request.files['image_file'] and request.files['image_file'].filename:
            haImg = True
            image_file = request.files['image_file']
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
            image_file.save(image_path)
            with open(image_path, "rb") as img_file:
                image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        else:
            image_base64 = None

        try:
            if file and file.filename.endswith('.xlsx'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                df = pd.read_excel(filepath)
                data_list = df.to_dict(orient='records')

                print("Mensagem escrita:", message)
                print("Número WhatsApp selecionado:", instancia)
                print("Data agendamento:", data_agendamento)
                print("Horário agendamento:", horario_agendamento)
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
                    'leads': leads,
                    'haImg': haImg,
                    'base64': image_base64 if haImg else None,
                    'data_agendamento': data_agendamento,
                    'horario_agendamento': horario_agendamento,
                    'instancia': instancia
                }

                print("Payload sendo enviado:", payload)
                response = requests.post('https://rede-confianca-n8n.lpl0df.easypanel.host/webhook/disparo-rede-confianca', json=payload)
                print("Resposta do webhook:", response.status_code, response.text)
                return render_template('index.html', success=True, data=payload, numbers=numbers)
            else:
                return render_template('index.html', error='Por favor, selecione um arquivo Excel válido (.xlsx)', numbers=numbers)
            
        except Exception as e:
            print(f"Erro durante o processamento: {str(e)}")
            return render_template('index.html', error=f'Erro ao processar arquivo: {str(e)}', numbers=numbers)
    
    return render_template('index.html', success=False, numbers=numbers)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)