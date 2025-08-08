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

def get_messages_from_chat(instance_name, remote_jid, limit=50):
    """Busca mensagens de um chat específico da Evolution API"""
    # Primeiro tenta buscar do banco de dados da Evolution
    connection = get_evolution_db_connection()
    messages = []
    
    if connection:
        try:
            cursor = connection.cursor(dictionary=True)
            query = """
            SELECT m.*, c.name as contact_name 
            FROM Message m 
            LEFT JOIN Contact c ON m.remoteJid = c.remoteJid AND m.instance = c.instance
            WHERE m.instance = %s AND m.remoteJid = %s 
            ORDER BY m.messageTimestamp DESC 
            LIMIT %s
            """
            cursor.execute(query, (instance_name, remote_jid, limit))
            messages = cursor.fetchall()
            print(f"Mensagens encontradas no banco: {len(messages)}")
            
        except Error as e:
            print(f"Erro ao buscar mensagens do banco: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    
    # Se não encontrou mensagens no banco, tenta buscar via API
    if not messages:
        try:
            print("Tentando buscar mensagens via API Evolution...")
            url = f"{os.getenv('EVOLUTION_BASE_URL', '')}/chat/findMessages/{instance_name}"
            headers = get_evolution_api_headers()
            
            payload = {
                "where": {
                    "remoteJid": remote_jid
                },
                "limit": limit
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                api_data = response.json()
                if api_data and 'data' in api_data:
                    messages = api_data['data']
                    print(f"Mensagens encontradas via API: {len(messages)}")
                else:
                    print("Nenhuma mensagem encontrada via API")
            else:
                print(f"Erro na API Evolution: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Erro ao buscar mensagens via API: {e}")
    
    # Processar mensagens para formato mais amigável
    for msg in messages:
        if msg.get('messageTimestamp'):
            import datetime
            try:
                timestamp = int(msg['messageTimestamp']) / 1000
                msg['formatted_time'] = datetime.datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')
            except:
                msg['formatted_time'] = 'Data inválida'
        else:
            msg['formatted_time'] = 'Sem data'
    
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
        # Reiniciar a instância na Evolution API
        restart_url = f"{os.getenv('EVOLUTION_BASE_URL', '')}/instance/restart/{instancia}"
        headers = get_evolution_api_headers()
        
        restart_response = requests.post(restart_url, headers=headers)
        if restart_response.status_code == 201:
            print(f"Instância {instancia} reiniciada com sucesso")
            # Redirecionar para a página de criação com QR Code
            return render_template('criar_numero.html', 
                                 instancia=instancia, 
                                 step=2,  # Pular para o step do QR Code
                                 reconnect=True)  # Flag para indicar que é reconexão
        else:
            print(f"Erro ao reiniciar instância: {restart_response.text}")
            return f"Erro ao reiniciar instância: {restart_response.text}", 400
            
    except Exception as e:
        print(f"Erro ao reconectar: {e}")
        return f"Erro ao reconectar: {str(e)}", 500

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

                    leads.append({
                        'filial': str(filial) if filial else '',
                        'data': str(data) if data else '',
                        'nome': str(nome) if nome else '',
                        'plano': str(plano) if plano else '',
                        'telefone': str(telefone) if telefone else ''
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