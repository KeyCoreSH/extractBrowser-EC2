# 🚀 ExtractBrowser EC2 v0.1

Sistema inteligente de extração e estruturação de dados de documentos brasileiros rodando no EC2.

[![Status](https://img.shields.io/badge/status-ativo-green)](https://extract.logt.com.br)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-3.0+-red)](https://flask.palletsprojects.com)
[![AWS](https://img.shields.io/badge/aws-ec2%20%7C%20s3%20%7C%20textract-orange)](https://aws.amazon.com)

## 🌐 Demo

**Acesse o sistema em produção:** [https://extract.logt.com.br](https://extract.logt.com.br)

## ✨ Funcionalidades

### 📄 **Processamento Inteligente de Documentos**
- **Extração automática** de texto de PDFs e imagens
- **OCR inteligente** para documentos assinados/digitalizados
- **Detecção automática** de tipo de documento
- **Preview em alta qualidade** da primeira página de PDFs

### 🤖 **IA e Estruturação de Dados**
- **OpenAI GPT-4o-mini** para estruturação inteligente
- **Prompts específicos** para cada tipo de documento
- **Validação automática** dos dados extraídos
- **Score de confiança** para cada extração

### 📋 **Tipos de Documentos Suportados**
- **CNH** - Carteira Nacional de Habilitação
- **CPF** - Cadastro de Pessoa Física  
- **CNPJ** - Cadastro Nacional de Pessoa Jurídica
- **ANTT** - Certificado de Condutor
- **CRV** - Certificado de Registro de Veículo
- **Fatura de Energia** Elétrica
- **Documentos genéricos**

### 🔧 **Tecnologias**
- **Backend**: Python 3.9+ com Flask
- **OCR**: AWS Textract + PyMuPDF
- **IA**: OpenAI GPT-4o-mini
- **Storage**: AWS S3
- **Frontend**: HTML5 + JavaScript vanilla
- **Deploy**: EC2 + Nginx + Systemd

## 🚀 Instalação e Uso

### 📋 **Pré-requisitos**

- Python 3.9+
- Conta AWS com acesso a S3 e Textract
- Chave da OpenAI API (opcional, para estruturação IA)

### 🔧 **Instalação Local**

```bash
# 1. Clonar o repositório
git clone <seu-repositorio>
cd extractBrowser-EC2

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp config.env.example .env
# Edite o .env com suas credenciais
```

### ⚙️ **Configuração do .env**

```bash
# OpenAI API Key (opcional)
OPENAI_API_KEY=sk-your-openai-key-here

# Configurações do servidor
PORT=2345
S3_BUCKET=extractbrowser-ec2-documents
AWS_REGION=us-east-2

# AWS Credentials (ou use aws configure)
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
```

### 🏃 **Executar Localmente**

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Iniciar servidor
python app.py

# Acessar aplicação
# Frontend: http://localhost:2345
# API: http://localhost:2345/health
```

### 🌐 **Interface Web**

Abra seu navegador e acesse `http://localhost:2345` ou abra o arquivo `frontend.html`.

## 📚 **Como Usar**

### 1. **Upload de Documento**
- Arraste um arquivo ou clique para selecionar
- Suporte: PDF, PNG, JPG, JPEG (máx. 10MB)
- Selecione o tipo de documento (opcional)

### 2. **Processamento Automático**
- **Extração de texto**: PyMuPDF + OCR inteligente
- **Análise de conteúdo**: Detecção automática do tipo
- **Estruturação IA**: OpenAI GPT-4o-mini
- **Validação**: Verificação de campos obrigatórios

### 3. **Resultados**
- **Dados estruturados**: JSON organizado por tipo
- **Preview visual**: Imagem da primeira página
- **Texto extraído**: Conteúdo completo detectado
- **Confiança**: Score de 0 a 100%

## 🔄 **Lógica OCR Inteligente**

O sistema decide automaticamente quando usar OCR:

```python
# Condições para OCR
texto_curto = len(texto_direto) < 50
documento_assinado = "assinado" in texto_direto.lower()

if texto_curto or documento_assinado:
    # Usa AWS Textract na imagem renderizada (400 DPI)
    usar_ocr()
else:
    # Usa texto direto do PDF
    usar_texto_direto()
```

## 📡 **API Endpoints**

### `GET /health`
Status e saúde do sistema
```json
{
  "status": "healthy",
  "dependencies": {
    "s3": true,
    "pdf_libs": true,
    "ai_service": true,
    "openai_available": true
  }
}
```

### `POST /upload`
Upload e processamento de documento
```bash
curl -X POST http://localhost:2345/upload \
  -F "file=@documento.pdf" \
  -F "document_type=cnh"
```

### `GET /view/<s3_key>`
Visualização de arquivos processados
```bash
curl http://localhost:2345/view/original_files/documento.pdf
```

### `GET /files`
Lista arquivos no bucket
```json
{
  "success": true,
  "files": [...],
  "count": 10
}
```

## 🚀 **Deploy no EC2**

### 📦 **Deploy Automático**

> [!IMPORTANT]  
> **Requisito de Versão Python**: Devido à dependência do `PyMuPDF` (biblioteca C++ compilada), recomenda-se usar **Python 3.9 a 3.11**.  
> O Python 3.13 ainda não possui rodas (wheels) pré-compiladas compatíveis, o que pode causar erros de compilação durante o deploy.

```bash
# 1. Configurar AWS CLI
aws configure

# 2. Executar script de deploy
chmod +x deploy.sh
./deploy.sh
```

### 🔧 **Deploy Manual**

```bash
# 1. Instalar dependências do sistema
sudo yum update -y
sudo yum install -y python3 python3-pip nginx

# 2. Configurar aplicação
sudo mkdir -p /opt/extractbrowser
sudo cp -r . /opt/extractbrowser/
cd /opt/extractbrowser

# 3. Instalar dependências Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configurar systemd
sudo cp deploy/extractbrowser.service /etc/systemd/system/
sudo systemctl enable extractbrowser
sudo systemctl start extractbrowser

# 5. Configurar Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/extractbrowser
sudo ln -s /etc/nginx/sites-available/extractbrowser /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## 🏗️ **Arquitetura**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API     │    │   AWS Services  │
│   (HTML/JS)     │◄──►│   (Python)      │◄──►│   (S3/Textract) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │   OpenAI API    │
                        │   (GPT-4o-mini) │
                        └─────────────────┘
```

### 📁 **Estrutura do Projeto**

```
extractBrowser-EC2/
├── app.py                 # 🚀 Servidor Flask principal
├── requirements.txt       # 📦 Dependências Python  
├── .env                   # 🔑 Variáveis de ambiente
├── deploy.sh             # ⚙️ Script de deploy EC2
├── frontend.html         # 🌐 Interface web
├── utils/                # 🔧 Utilitários
│   ├── pdf_extractor.py  # 📄 Extração PDF + OCR
│   └── s3_manager.py     # 🪣 Gerenciamento S3
├── services/             # 🤖 Serviços
│   └── ai_service.py     # 🧠 Integração OpenAI
└── prompts/              # 📝 Prompts IA
    ├── cnh_prompt.py     # 🚗 Prompt CNH
    └── base_prompt.py    # 📋 Prompts genéricos
```

## 🔒 **Segurança**

- **Variáveis de ambiente** para credenciais sensíveis
- **Validação rigorosa** de tipos de arquivo
- **Timeout nas requisições** para APIs externas
- **Sanitização** de dados de entrada
- **CORS configurado** adequadamente

## 📊 **Monitoramento**

### 🏥 **Health Check**
```bash
curl http://localhost:2345/health
```

### 📋 **Logs do Sistema**
```bash
# Ver logs do serviço
sudo journalctl -u extractbrowser -f

# Ver logs do Nginx
sudo tail -f /var/log/nginx/access.log
```

### 📈 **Performance**
- **Texto direto**: < 1 segundo
- **OCR com Textract**: 2-5 segundos  
- **Estruturação IA**: 3-8 segundos
- **Total típico**: 5-15 segundos

## 🛠️ **Desenvolvimento**

### 🧪 **Testes**

```bash
# Testar extração PDF
python utils/pdf_extractor.py

# Testar gerenciador S3
python utils/s3_manager.py

# Testar servidor
curl -X POST http://localhost:2345/upload \
  -F "file=@test.pdf" \
  -F "document_type=cnh"
```

### 🐛 **Debug**

```bash
# Logs detalhados
export FLASK_DEBUG=true
python app.py

# Verificar dependências
python -c "import fitz, requests, boto3; print('✅ Dependências OK')"
```

## ❓ **Solução de Problemas**

### 🔧 **Problemas Comuns**

**PyMuPDF não instala:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev

# CentOS/RHEL
sudo yum install python3-devel
```

**AWS Textract retorna erro:**
```bash
# Verificar credenciais
aws sts get-caller-identity

# Verificar região
export AWS_REGION=us-east-2
```

**OpenAI API falha:**
```bash
# Verificar chave
echo $OPENAI_API_KEY

# Testar conectividade
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

## 🤝 **Contribuição**

1. Fork o repositório
2. Crie sua branch: `git checkout -b feature/nova-funcionalidade`
3. Commit suas mudanças: `git commit -m 'Adiciona nova funcionalidade'`
4. Push para a branch: `git push origin feature/nova-funcionalidade`  
5. Abra um Pull Request

## 📝 **Licença**

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 **Agradecimentos**

- **AWS** - Infraestrutura e serviços
- **OpenAI** - API de inteligência artificial
- **PyMuPDF** - Biblioteca de processamento PDF
- **Flask** - Framework web Python

---

**🚀 Desenvolvido com ❤️ para facilitar a extração inteligente de documentos brasileiros!**

Para suporte: [https://extract.logt.com.br](https://extract.logt.com.br)