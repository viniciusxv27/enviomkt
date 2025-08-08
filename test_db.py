#!/usr/bin/env python3

import mysql.connector
from mysql.connector import Error

def test_evolution_db():
    try:
        print('=== Testando conexão com banco Evolution ===')
        connection = mysql.connector.connect(
            host='localhost',
            database='evolution',
            user='mysql',
            password='redeconfianca2025'
        )
        
        print('✅ Conexão OK!')
        cursor = connection.cursor()
        
        # Listar tabelas
        cursor.execute('SHOW TABLES')
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        print(f'📋 Tabelas encontradas: {table_names}')
        
        # Verificar se Contact existe
        if 'Contact' in table_names:
            cursor.execute("SELECT COUNT(*) FROM Contact")
            count = cursor.fetchone()[0]
            print(f'👥 Total de contatos: {count}')
            
            cursor.execute('SELECT DISTINCT instance FROM Contact LIMIT 10')
            instances = cursor.fetchall()
            instance_names = [inst[0] for inst in instances]
            print(f'🏢 Instâncias com contatos: {instance_names}')
            
            if instance_names:
                # Testar com uma instância específica
                test_instance = instance_names[0]
                cursor.execute("SELECT COUNT(*) FROM Contact WHERE instance = %s", (test_instance,))
                contact_count = cursor.fetchone()[0]
                print(f'👤 Contatos na instância {test_instance}: {contact_count}')
                
                # Mostrar alguns contatos
                cursor.execute("SELECT remoteJid, name, pushName FROM Contact WHERE instance = %s LIMIT 5", (test_instance,))
                contacts = cursor.fetchall()
                print(f'📞 Amostra de contatos:')
                for contact in contacts:
                    print(f'  - {contact[0]} | {contact[1]} | {contact[2]}')
        else:
            print('❌ Tabela Contact não encontrada')
        
        # Verificar se Message existe
        if 'Message' in table_names:
            cursor.execute("SELECT COUNT(*) FROM Message")
            count = cursor.fetchone()[0]
            print(f'💬 Total de mensagens: {count}')
            
            cursor.execute('SELECT DISTINCT instance FROM Message LIMIT 10')
            instances = cursor.fetchall()
            instance_names = [inst[0] for inst in instances]
            print(f'🏢 Instâncias com mensagens: {instance_names}')
            
            if instance_names:
                test_instance = instance_names[0]
                cursor.execute("SELECT DISTINCT remoteJid FROM Message WHERE instance = %s AND remoteJid NOT LIKE '%@g.us' LIMIT 5", (test_instance,))
                message_contacts = cursor.fetchall()
                print(f'📱 Contatos com mensagens na instância {test_instance}:')
                for contact in message_contacts:
                    print(f'  - {contact[0]}')
        else:
            print('❌ Tabela Message não encontrada')
        
        connection.close()
        print('✅ Teste concluído!')
        
    except Error as e:
        print(f'❌ Erro de conexão: {e}')

if __name__ == '__main__':
    test_evolution_db()
