#!/bin/bash

# Script para iniciar a aplicação de Broadcast WhatsApp

echo "🚀 Iniciando Sistema de Broadcast WhatsApp - VIVO"
echo "================================================="

# Verificar se o ambiente virtual existe
if [ ! -d ".venv" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "📦 Criando ambiente virtual..."
    python3 -m venv .venv
fi

# Ativar ambiente virtual
echo "🔄 Ativando ambiente virtual..."
source .venv/bin/activate

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Verificar se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "📝 Copie o arquivo .env.example para .env e configure suas credenciais"
    echo "cp .env.example .env"
    exit 1
fi

echo "✅ Tudo pronto!"
echo ""
echo "🌐 Iniciando servidor na porta 8000..."
echo "📱 Acesse: http://localhost:8000"
echo ""
echo "⏹️  Para parar o servidor, pressione Ctrl+C"
echo ""

# Iniciar aplicação
python3 app.py
