from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
import requests
from dotenv import load_dotenv
import base64
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
logado = False
load_dotenv()

# Configuração do banco de dados
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'whatsapp'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        return connection
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None

def get_whatsapp_numbers():
    """Busca todos os números do WhatsApp cadastrados"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT numero, remotejid, descricao, instancia FROM numeros ORDER BY id"
        cursor.execute(query)
        numbers = cursor.fetchall()
        return numbers
    except Error as e:
        print(f"Erro ao buscar números: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def create_whatsapp_number(numero, remotejid, descricao, instancia):
    """Cria um novo número do WhatsApp"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
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
        numero = request.form.get('numero', '').strip()
        remotejid = request.form.get('remotejid', '').strip()
        descricao = request.form.get('descricao', '').strip()
        instancia = request.form.get('instancia', '').strip()
        
        if not all([numero, remotejid, descricao, instancia]):
            return render_template('criar_numero.html', error='Todos os campos são obrigatórios')
        
        if create_whatsapp_number(numero, remotejid, descricao, instancia):
            return redirect(url_for('numeros'))
        else:
            return render_template('criar_numero.html', error='Erro ao criar número')
    
    return render_template('criar_numero.html')

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
                    'instancia': whatsapp_number
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