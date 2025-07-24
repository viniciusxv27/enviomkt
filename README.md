# 📢 Sistema de Broadcast WhatsApp - VIVO

Sistema para envio de mensagens em massa via WhatsApp com agendamento e gestão de números.

## 🚀 Funcionalidades

- ✅ Envio de mensagens em massa via WhatsApp
- ✅ Upload de arquivo Excel com dados dos clientes
- ✅ Anexo de imagens nas mensagens
- ✅ Agendamento de envios (data e hora)
- ✅ Gestão de múltiplos números do WhatsApp
- ✅ Sistema de autenticação
- ✅ Variáveis dinâmicas nas mensagens (@nome, @filial, @data, @plano, @telefone)

## 📋 Pré-requisitos

- Python 3.8+
- MySQL 5.7+ ou 8.0+
- Banco de dados configurado

## 🛠️ Instalação

1. **Clone o repositório e instale as dependências:**
   ```bash
   cd enviomkt
   pip install -r requirements.txt
   ```

2. **Configure o banco de dados:**
   - Execute o script `database.sql` no seu MySQL:
   ```sql
   mysql -u root -p < database.sql
   ```

3. **Configure as variáveis de ambiente:**
   - Copie o arquivo `.env.example` para `.env`
   - Configure suas credenciais:
   ```env
   USERNAME=seu_usuario
   PASSWORD=sua_senha
   DB_HOST=localhost
   DB_NAME=whatsapp
   DB_USER=root
   DB_PASSWORD=sua_senha_mysql
   ```

4. **Execute a aplicação:**
   ```bash
   python3 app.py
   ```

5. **Acesse o sistema:**
   - Abra o navegador em: `http://localhost:5000`

## 📱 Configuração dos Números WhatsApp

1. **Acesse "Gerenciar Números WhatsApp"** na tela principal
2. **Clique em "Adicionar Número"**
3. **Preencha os dados:**
   - **Número:** +5511999999999
   - **Remote JID:** 5511999999999@s.whatsapp.net  
   - **Descrição:** WhatsApp Vendas - Centro
   - **Instância:** instance_01

## 📊 Formato do Arquivo Excel

O arquivo Excel deve conter as seguintes colunas:
- **Filial:** Nome da loja/filial
- **Data:** Data da compra
- **Nome Cliente:** Nome completo do cliente
- **Plano:** Plano contratado
- **Acesso:** Número do telefone do cliente

## 💬 Variáveis da Mensagem

Use estas variáveis na sua mensagem:
- `@nome` - Nome do cliente
- `@filial` - Loja que comprou
- `@data` - Data da compra
- `@plano` - Plano contratado
- `@telefone` - Número do cliente

**Exemplo de mensagem:**
```
Olá @nome! 👋

Obrigado por escolher a VIVO na filial @filial em @data.

Seu plano @plano já está ativo no número @telefone.

Dúvidas? Entre em contato!
```

## 🔧 Estrutura do Projeto

```
enviomkt/
├── app.py                    # Aplicação principal
├── requirements.txt          # Dependências Python
├── database.sql             # Script de criação do banco
├── .env.example            # Exemplo de configuração
├── templates/
│   ├── index.html          # Página principal
│   ├── login.html          # Página de login
│   ├── numeros.html        # Lista de números
│   └── criar_numero.html   # Cadastro de números
├── static/
│   └── style.css          # Estilos CSS
└── uploads/               # Arquivos temporários
```

## 🚀 Produção

Para rodar em produção, considere usar:
- **Gunicorn** como servidor WSGI
- **Nginx** como proxy reverso
- **Supervisor** para gerenciar o processo
- **SSL/HTTPS** para segurança

## 📞 Suporte

Para dúvidas ou problemas, verifique:
1. Logs do console Python
2. Configuração do banco de dados
3. Variáveis de ambiente no arquivo `.env`
4. Permissões dos diretórios de upload
