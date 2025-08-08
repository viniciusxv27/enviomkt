#!/usr/bin/env python3
"""
Script de teste para verificar a conexão com a Evolution API
Execute este script para testar se as configurações estão corretas
"""

import os
import requests
from dotenv import load_dotenv

def test_evolution_api():
    load_dotenv()
    
    base_url = os.getenv('EVOLUTION_BASE_URL', '')
    api_key = os.getenv('EVOLUTION_API_KEY', '')
    
    print("🧪 TESTE DE CONEXÃO COM EVOLUTION API")
    print("=" * 50)
    print(f"📍 Base URL: {base_url}")
    print(f"🔑 API Key: {'*' * 20}{api_key[-4:] if len(api_key) > 4 else 'VAZIO'}")
    print()
    
    headers = {
        'Content-Type': 'application/json',
        'apikey': api_key
    }
    
    # Teste 1: Verificar se a API responde
    print("1️⃣ Testando conectividade básica...")
    try:
        response = requests.get(f"{base_url}/instance/fetchInstances", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Resposta: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
        
        if response.status_code == 200:
            print("   ✅ API acessível!")
        else:
            print("   ❌ API retornou erro")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro de conexão: {e}")
        return False
    
    # Teste 2: Tentar criar instância de teste
    print("\n2️⃣ Testando criação de instância...")
    test_instance = "test_connection_123"
    
    try:
        payload = {
            "instanceName": test_instance,
            "token": api_key,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        
        response = requests.post(f"{base_url}/instance/create", json=payload, headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        print(f"   Resposta: {response.text[:200]}{'...' if len(response.text) > 200 else ''}")
        
        if response.status_code in [200, 201]:
            print("   ✅ Instância criada com sucesso!")
            
            # Teste 3: Buscar QR Code
            print("\n3️⃣ Testando busca de QR Code...")
            response = requests.get(f"{base_url}/instance/connect/{test_instance}", headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'qrcode' in data or 'base64' in data or 'qr' in data:
                    print("   ✅ QR Code obtido com sucesso!")
                else:
                    print(f"   ⚠️ QR Code não encontrado. Campos disponíveis: {list(data.keys())}")
            else:
                print("   ❌ Erro ao buscar QR Code")
            
            # Limpeza: Deletar instância de teste
            print("\n🧹 Limpando instância de teste...")
            try:
                requests.delete(f"{base_url}/instance/delete/{test_instance}", headers=headers, timeout=10)
                print("   ✅ Instância de teste removida")
            except:
                print("   ⚠️ Não foi possível remover a instância de teste")
                
        else:
            print("   ❌ Falha ao criar instância")
            
    except Exception as e:
        print(f"   ❌ Erro no teste: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 TESTE CONCLUÍDO")
    return True

if __name__ == "__main__":
    test_evolution_api()
