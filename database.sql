-- Script para criar as tabelas necessárias para o sistema
-- Execute este script no seu banco MySQL PRINCIPAL (não no da Evolution)

-- Tabela para números do WhatsApp (banco principal)
CREATE TABLE IF NOT EXISTS whatsapp_numbers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero VARCHAR(20) NOT NULL,
    remotejid VARCHAR(100) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    instancia VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Criar índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_remotejid ON whatsapp_numbers(remotejid);
CREATE INDEX IF NOT EXISTS idx_instancia ON whatsapp_numbers(instancia);

-- Inserir alguns dados de exemplo (opcional)
-- INSERT INTO whatsapp_numbers (numero, remotejid, descricao, instancia) VALUES
-- ('+5511999999999', '5511999999999@s.whatsapp.net', 'WhatsApp Principal - Vendas', 'instance_01'),
-- ('+5511888888888', '5511888888888@s.whatsapp.net', 'WhatsApp Suporte - Atendimento', 'instance_02');

-- IMPORTANTE: 
-- As tabelas da Evolution API (Instance, Message, Contact) devem existir no banco da Evolution API
-- Não execute essas tabelas no banco principal do sistema!
-- O sistema se conectará aos dois bancos separadamente.
