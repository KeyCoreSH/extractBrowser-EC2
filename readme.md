# 🚀 ExtractBrowser EC2 v0.2

Sistema inteligente de extração e estruturação de dados de documentos brasileiros.

[![Status](https://img.shields.io/badge/status-ativo-green)](https://extract.logt.com.br)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.13-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-3.0+-red)](https://flask.palletsprojects.com)
[![AI](https://img.shields.io/badge/OpenAI-GPT--4o-purple)](https://openai.com)

## ✨ Funcionalidades

### 📄 **Processamento Inteligente**
- **Extração Híbrida**: Combina extração de texto nativo (PyMuPDF) com OCR avançado (AWS Textract) quando necessário.
- **Robustez "Digital Certificate"**: Detecta automaticamente documentos com camadas de texto placeholder ("Assinado digitalmente") e força OCR para extrair o conteúdo visual real.
- **Detecção Automática**: Identifica o tipo de documento (CNH, CRLV, ANTT, Faturas) automaticamente.
- **Estruturação via IA**: Utiliza **GPT-4o** para garantir máxima precisão e conformidade com JSON estrito.

### 📋 **Tipos de Documentos Suportados**
1. **ANTT** (Certificados e Extratos)
2. **CNH** (Carteira Nacional de Habilitação)
3. **CNPJ** (Comprovante de Inscrição)
4. **Veículo** (CRLV Digital, CRV, Fichas)
5. **Residência** (Contas de Luz, Água, Gás, Internet)

---

## �️ Tecnologias e Configuração

- **Linguagem**: Python 3.10+ (Compatível com 3.13)
- **Framework**: Flask
- **IA Model**: GPT-4o (Otimizado para raciocínio complexo)
- **OCR**: AWS Textract
- **Banco de Dados**: SQLite (Local/Dev) / RDS (Prod)

### Instalação

1. **Clone o repositório:**
   ```bash
   git clone <repo-url>
   cd extractBrowser-EC2
   ```

2. **Configure o ambiente:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure as variáveis (.env):**
   ```bash
   cp config.env.example .env
   # Defina: OPENAI_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
   # Defina: OPENAI_MODEL=gpt-4o
   ```

4. **Execute:**
   ```bash
   python app.py
   # Acesso: http://localhost:2345
   # Login Padrão: adm@keycore.com.br / "solicitar acesso"
   ```

---

## 🔐 Autenticação via API (Programática)

Para acessar os endpoints (como `/upload`) programaticamente sem cookies de sessão, utilize a **API Token**.

### Configuração
Defina a variável `API_ACCESS_TOKEN` no seu `.env` ou nas variáveis de ambiente do servidor.

### Exemplos de Uso

**Opção 1: Header `X-API-Key`**
```bash
curl -X POST https://seu-dominio.com/upload \
  -H "X-API-Key: sua-chave-aqui" \
  -F "file=@documento.pdf"
```

**Opção 2: Header `Authorization` (Bearer)**
```bash
curl -X POST https://seu-dominio.com/upload \
  -H "Authorization: Bearer sua-chave-aqui" \
  -F "file=@documento.pdf"
```

---

## 📦 Schemas de Retorno (JSON Exato)

O sistema garante que o retorno da API `/upload` siga estritamente os formatos abaixo dentro do campo `structured_data.data`.

### 1. ANTT (Certificado/Extrato)
```json
{
  "tipo_documento": "CERTIFICADO_ANTT",
  "transportador": {
    "rntrc": "00000000",
    "razao_social_nome": "EMPRESA EXEMPLO LTDA",
    "cpf_cnpj": "00.000.000/0001-00",
    "situacao_rntrc": "ATIVO",
    "categoria": "ETC",
    "data_validade": "DD/MM/AAAA",
    "data_emissao": "DD/MM/AAAA"
  },
  "endereco": {
    "logradouro": "RUA EXEMPLO",
    "numero": "123",
    "bairro": "CENTRO",
    "cidade": "CIDADE",
    "uf": "UF",
    "cep": "00000-000"
  },
  "resumo_frota": {
    "total_veiculos": 10,
    "veiculos_ativos": 8
  },
  "veiculos": [
    {
      "placa": "ABC-1234",
      "renavam": "00000000000",
      "tipo": "Automotor",
      "tipo_carroceria": "Caminhão Trator",
      "situacao": "Ativo",
      "propriedade": "Próprio"
    }
  ]
}
```

### 2. CNH (Carteira de Habilitação)
```json
{
  "nome": "NOME COMPLETO DO PORTADOR",
  "cpf": "000.000.000-00",
  "rg": "00000000",
  "data_nascimento": "DD/MM/AAAA",
  "data_emissao": "DD/MM/AAAA",
  "data_validade": "DD/MM/AAAA",
  "categoria": "AB",
  "numero_registro": "00000000000",
  "local_emissao": "CIDADE/UF",
  "filiacao": {
    "pai": "NOME DO PAI",
    "mae": "NOME DA MAE"
  },
  "endereco": "ENDEREÇO COMPLETO EXTRAÍDO",
  "observacoes": "EAR"
}
```

### 3. CNPJ (Cartão CNPJ)
```json
{
  "cnpj": "00.000.000/0001-00",
  "razao_social": "RAZÃO SOCIAL DA EMPRESA",
  "nome_fantasia": "NOME FANTASIA",
  "data_abertura": "DD/MM/AAAA",
  "situacao_cadastral": "ATIVA",
  "natureza_juridica": "206-2 - SOCIEDADE EMPRESARIA LIMITADA",
  "atividades_economicas": [
    {
      "codigo": "00.00-0-00",
      "descricao": "Descrição da atividade econômica"
    }
  ],
  "endereco": {
    "logradouro": "RUA EXEMPLO",
    "numero": "100",
    "bairro": "BAIRRO",
    "municipio": "CIDADE",
    "uf": "UF",
    "cep": "00000-000"
  },
  "contato": {
    "telefone_1": "(00) 0000-0000",
    "email": "contato@empresa.com.br"
  },
  "socios": [
    {
      "nome": "NOME DO SÓCIO",
      "qualificacao": "Sócio-Administrador"
    }
  ],
  "capital_social": "R$ 100.000,00"
}
```

### 4. Veículo (CRLV-e / CRV)
```json
{
  "tipo_documento": "CRLV",
  "dados_veiculo": {
    "placa": "ABC1D23",
    "renavam": "00000000000",
    "chassi": "ABCD1234567890",
    "marca_modelo": "MARCA/MODELO VEICULO",
    "ano_fabricacao": 2024,
    "ano_modelo": 2024,
    "cor": "BRANCA",
    "combustivel": "DIESEL",
    "categoria": "PARTICULAR",
    "potencia_cilindrada": "150CV",
    "peso_bruto_total": "3500",
    "numero_eixos": "2"
  },
  "situacao": {
    "exercicio": "2024",
    "observacoes": "SEM RESERVA",
    "mensagem_senatran": "Mensagem administrativa se houver"
  },
  "proprietario": {
    "nome": "NOME DO PROPRIETARIO",
    "cpf_cnpj": "000.000.000-00",
    "local": "CIDADE",
    "uf": "UF"
  }
}
```

### 5. Residência (Comprovante / Fatura)
```json
{
  "tipo_documento": "CONTA_ENERGIA",
  "concessionaria": {
    "nome": "NOME DA CONCESSIONARIA",
    "cnpj": "00.000.000/0001-00"
  },
  "dados_conta": {
    "mes_referencia": "MM/AAAA",
    "vencimento": "AAAA-MM-DD",
    "valor_total": 150.50,
    "numero_instalacao": "000000000",
    "codigo_barras": "83600000..."
  },
  "cliente": {
    "nome": "NOME DO CLIENTE",
    "cpf_cnpj": "000.000.000-00"
  },
  "endereco_instalacao": {
    "logradouro": "RUA DA INSTALAÇÃO",
    "numero": "50",
    "cep": "00000-000",
    "municipio": "CIDADE",
    "uf": "UF"
  },
  "leituras": {
    "leitura_atual": "10500",
    "leitura_anterior": "10200",
    "consumo_faturado": "300 kWh"
  }
}
```

---

## ⚠️ Limitações Conhecidas e Melhorias Futuras

1.  **Processamento Síncrono**: O endpoint `/upload` processa o arquivo na hora. Para arquivos muito grandes ou alta carga, recomenda-se migrar para processamento assíncrono (filas SQS/RabbitMQ).
2.  **Autenticação**: O sistema atual usa uma implementação básica de usuário `admin` no banco SQLite. Para produção, integrar com OAuth2 ou sistema de usuários mais robusto.
3.  **Rate Limiting**: Implementado via Flask-Talisman/Limiter, mas deve ser ajustado conforme a infraestrutura (Load Balancer/WAF).
4.  **Monitoramento**: Logs são gerados no console e arquivo. Recomenda-se integração com CloudWatch ou ELK Stack para produção.

---

**Desenvolvido por KeyCore Tech Hub**