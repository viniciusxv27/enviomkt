from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
import requests
from dotenv import load_dotenv
import base64

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
logado = False
load_dotenv()

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

@app.route('/', methods=['GET', 'POST'])
def index():# Verifica se o usuário está autenticado
    if not logado:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['excel_file']
        message = request.form['message']
        haImg = False
        leads = []

        if request.files['image_file']:
            haImg = True
            image_file = request.files['image_file']
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
            image_file.save(image_path)
            with open(image_path, "rb") as img_file:
                image_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        try:
            if file and file.filename.endswith('.xlsx'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                df = pd.read_excel(filepath)
                data_list = df.to_dict(orient='records')

                print("Mensagem escrita:", message)
                print("Dados importados:")
                for row in data_list:
                    filial = row.get('Filial')
                    data = row.get('Data')
                    nome = row.get('Nome Cliente')
                    plano = row.get('Plano')
                    telefone = row.get('Acesso')

                    leads.append({
                        'filial': str(filial),
                        'data': str(data),
                        'nome': str(nome),
                        'plano': str(plano),
                        'telefone': str(telefone)
                    })

                payload = {
                    'message': message,
                    'leads': leads,
                    'haImg': haImg,
                    'base64': image_base64 if haImg else None
                }

                requests.post('https://rede-confianca-n8n.lpl0df.easypanel.host/webhook/disparo-rede-confianca', json=payload)  # Substitua pela URL do seu endpoint
                return render_template('index.html', success=True, data=payload)
            
        except ValueError:
            if file and file.filename.endswith('.xlsx'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                df = pd.read_excel(filepath)
                data_list = df.to_dict(orient='records')  # Converte cada linha em um dicionário

                # Aqui você pode usar os dados e aplicar lógica de envio, por exemplo:
                print("Mensagem escrita:", message)
                print("Dados importados:")
                for row in data_list:
                    print(row)

                return render_template('index.html', success=True, data=data_list)

    return render_template('index.html', success=False)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)