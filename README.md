# 📢 Sistema de Broadcast WhatsApp - VIVO

Sistema integrado com Evolution API para envio de mensagens em massa via WhatsApp com gestão completa de instâncias.

## 🚀 Funcionalidades

- ✅ **Integração com Evolution API** - Criação e gestão automática de instâncias
- ✅ **Dual Database Architecture** - Banco próprio + Integration com banco Evolution
- ✅ **Envio de mensagens em massa** via WhatsApp
- ✅ **Upload de arquivo Excel** com dados dos clientes
- ✅ **Anexo de imagens** nas mensagens
- ✅ **Agendamento de envios** (data e hora)
- ✅ **Gestão de múltiplos números** do WhatsApp
- ✅ **Monitoramento de status** - Conectado/Desconectado em tempo real
- ✅ **Visualizador de mensagens** estilo WhatsApp
- ✅ **Edição de descrições** dos números
- ✅ **Sistema de autenticação**
- ✅ **Variáveis dinâmicas** nas mensagens (@nome, @filial, @data, @plano, @telefone)

## 📋 Pré-requisitos

- Python 3.8+
- MySQL 5.7+ ou 8.0+
- **Evolution API** configurada e rodando
- **Dois bancos de dados:**
  - Banco principal do sistema
  - Banco da Evolution API (apenas leitura para mensagens e status)

## 🛠️ Instalação

1. **Clone o repositório e instale as dependências:**
   ```bash
   cd enviomkt
   pip install -r requirements.txt
   ```

2. **Configure o banco de dados:**
   - Use o **mesmo banco da Evolution API**
   - Execute apenas a parte da tabela `numeros` do script `database.sql`:
   ```sql
   mysql -u root -p evolution < database.sql
   ```

3. **Configure as variáveis de ambiente:**
   - Copie o arquivo `.env.example` para `.env`
   - Configure suas credenciais:
   ```env
   USERNAME=seu_usuario
   PASSWORD=sua_senha
   
   # Mesmo banco da Evolution API
   DB_HOST=localhost
   DB_NAME=evolution
   DB_USER=root
   DB_PASSWORD=sua_senha_mysql
   
   # Evolution API
   EVOLUTION_API_KEY=sua_api_key
   EVOLUTION_BASE_URL=http://localhost:8080
   ```

4. **Execute a aplicação:**
   ```bash
   python3 app.py
   ```

5. **Acesse o sistema:**
   - Abra o navegador em: `http://localhost:8000`

## 📱 Configuração dos Números WhatsApp

### 🚀 **Processo Automático com QR Code**

1. **Acesse "Gerenciar Números WhatsApp"** na tela principal
2. **Clique em "Adicionar Número"**
3. **Siga os 3 passos automáticos:**

#### 📱 **Passo 1: Criar Instância**
- Digite um nome único (ex: `vendas_centro_01`)
- Clique em "🚀 Criar Instância"

#### 📷 **Passo 2: Conectar WhatsApp**
- QR Code é exibido automaticamente
- Escaneie com WhatsApp: Menu → WhatsApp Web → Escanear
- Sistema verifica conexão em tempo real

#### 📝 **Passo 3: Cadastrar Dados**
- Preencha número, Remote JID e descrição
- Botão só é habilitado após WhatsApp conectado
- Salve o número

### ✨ **Funcionalidades Automáticas:**
- ✅ **QR Code gerado** automaticamente
- ✅ **Status verificado** a cada 3 segundos
- ✅ **Botão habilitado** só após conexão
- ✅ **Instância criada** na Evolution API
- ✅ **Conexão monitorada** em tempo real

## 🔧 Funcionalidades da Interface

### 📊 **Lista de Números**
- **Status em tempo real:** Conectado/Desconectado/Conectando
- **Botão Editar:** Permite alterar apenas a descrição
- **Botão Mensagens:** Visualiza conversas estilo WhatsApp

### 💬 **Visualizador de Mensagens**
- Interface similar ao WhatsApp
- Mensagens enviadas e recebidas
- Timestamps das mensagens
- Suporte a diferentes tipos de mídia
- Auto-scroll para mensagens mais recentes

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

## �️ **Estrutura do Banco**

O sistema usa o **mesmo banco da Evolution API** com uma tabela adicional:

```sql
-- Tabela adicional para gestão de números
CREATE TABLE numeros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero VARCHAR(20) NOT NULL,
    remotejid VARCHAR(100) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    instancia VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## �🔧 Estrutura do Projeto

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
│   ├── criar_numero.html   # Cadastro de números
│   ├── editar_numero.html  # Edição de números
│   └── mensagens.html      # Visualizador de mensagens
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

## ⚠️ **Importante**

1. **Use o mesmo banco da Evolution API** para acessar mensagens e status
2. **Configure corretamente** as variáveis da Evolution API
3. **Mantenha a Evolution API** rodando para funcionalidade completa
4. **Teste a conexão** antes de usar em produção

## 📞 Suporte

Para dúvidas ou problemas, verifique:
1. Logs do console Python
2. Status da Evolution API
3. Configuração do banco de dados
4. Variáveis de ambiente no arquivo `.env`
5. Permissões dos diretórios de upload
