#!/usr/bin/env python3
"""
ExtractBrowser EC2 - Serviço de extração de documentos
Servidor web Python para processar PDFs e imagens no EC2
"""

import os
import sys
import json
import time
import base64
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
from flask_talisman import Talisman
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Módulos locais
from utils.pdf_extractor import extract_pdf_preview, get_pdf_info, validate_pdf, extract_text_from_pdf, extract_text_from_image
from utils.s3_manager import S3Manager
from services.ai_service import AIService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
PORT = int(os.environ.get('PORT', 2345))
S3_BUCKET = os.environ.get('S3_BUCKET', 'extractbrowser-ec2-documents')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-2')

# Inicializar Flask
app = Flask(__name__)
CORS(app, origins=['*'])  # Permitir todas as origens por enquanto
# Configurar headers de segurança com Talisman
# CSP permissiva para permitir estilos inline e CDNs externos (Font Awesome)
csp = {
    'default-src': ["'self'", "'unsafe-inline'", 'data:', 'blob:'],
    'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", 'https://cdnjs.cloudflare.com'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://cdnjs.cloudflare.com', 'https://fonts.googleapis.com'],
    'font-src': ["'self'", 'data:', 'https://cdnjs.cloudflare.com', 'https://fonts.gstatic.com'],
    'img-src': ["'self'", 'data:', 'blob:', 'https://*.amazonaws.com']
}
# Desabilitar session_cookie_secure para rodar em HTTP localmente
Talisman(app, force_https=False, content_security_policy=csp, session_cookie_secure=False)

# Gerenciador S3 e Serviço de IA
s3_manager = None
ai_service = None

# Configuração de Banco de Dados e Autenticação
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from database import db, User, ExtractionLog
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração do Banco de Dados
db_path = os.path.join(os.getcwd(), 'data', 'extractbrowser.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'keycore-secret-key-change-me')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def init_db():
    """Inicializar banco de dados e usuário admin"""
    with app.app_context():
        # Evitar race condition na criação das tabelas
        try:
            db.create_all()
        except Exception as e:
            logger.info(f"ℹ️ Tabelas já existem ou erro de concorrência: {e}")

        # Verificar se admin existe
        admin = User.query.filter_by(email='adm@keycore.com.br').first()
        if not admin:
            try:
                hashed_password = generate_password_hash('R0ger!n20100')
                admin = User(
                    email='adm@keycore.com.br',
                    password_hash=hashed_password,
                    name='Admin KeyCore'
                )
                db.session.add(admin)
                db.session.commit()
                logger.info("✅ Usuário admin criado")
            except Exception as e:
                # Pode ocorrer erro de integridade se outro worker criar ao mesmo tempo
                db.session.rollback()
                logger.info(f"ℹ️ Usuário admin já existe (race condition handled): {e}")
        else:
            logger.info("ℹ️ Usuário admin já existe")

def init_s3_manager():
    """Inicializar gerenciador S3"""
    global s3_manager
    try:
        s3_manager = S3Manager(S3_BUCKET, AWS_REGION)
        # Criar bucket se não existir
        s3_manager.create_bucket_if_not_exists()
        logger.info(f"✅ S3Manager inicializado para bucket {S3_BUCKET}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar S3Manager: {e}")
        return False

def init_ai_service():
    """Inicializar serviço de IA"""
    global ai_service
    try:
        ai_service = AIService()
        logger.info("✅ Serviço de IA inicializado")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar serviço de IA: {e}")
        return False

def check_pdf_dependencies():
    """Verificar se dependências de PDF estão disponíveis"""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        logger.info("✅ Dependências PyMuPDF e Pillow disponíveis")
        return True
    except ImportError as e:
        logger.error(f"❌ Dependências não disponíveis: {e}")
        return False

def create_standardized_response(success: bool, message: str, document_type: str = "", 
                               structured_data: Dict[str, Any] = None, 
                               processing_time_ms: int = 0, 
                               additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Cria resposta padronizada conforme exemplo fornecido
    
    Args:
        success: Se a operação foi bem-sucedida
        message: Mensagem descritiva
        document_type: Tipo do documento processado
        structured_data: Dados estruturados extraídos
        processing_time_ms: Tempo de processamento em milissegundos
        additional_data: Dados adicionais para incluir
        
    Returns:
        Resposta padronizada
    """
    if structured_data is None:
        structured_data = {}
    if additional_data is None:
        additional_data = {}
    
    response = {
        "success": success,
        "message": message,
        "data": {
            "document_type": document_type.upper() if document_type else "UNKNOWN",
            "data": structured_data,
            "processing_time_ms": processing_time_ms
        }
    }
    
    # Adicionar dados extras se fornecidos
    if additional_data:
        for key, value in additional_data.items():
            if value is not None:  # Só adicionar se tiver valor
                response["data"][key] = value
    
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login"""
    from flask import redirect, url_for, flash
    
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        # Suporte a JSON e Form Data
        if request.is_json:
            data = request.json
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            logger.info(f"🔑 Login realizado: {email}")
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login realizado com sucesso',
                    'user': {'email': user.email, 'name': user.name}
                })
            return redirect(url_for('index'))
        else:
            logger.warning(f"❌ Falha de login: {email}")
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email ou senha inválidos'}), 401
            flash('Email ou senha inválidos')
            
    # Template login com AJAX e LocalStorage
    login_html = '''<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - ExtractBrowser</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .login-card {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        .login-header h2 { color: #667eea; margin-bottom: 20px; }
        .input-group { margin-bottom: 20px; text-align: left; }
        .input-group label { display: block; margin-bottom: 5px; color: #666; }
        .input-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        .login-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 25px;
            font-size: 1.1em;
            cursor: pointer;
            width: 100%;
            font-weight: 600;
        }
        .error-msg {
            color: #721c24;
            background: #f8d7da;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-header">
            <h2><i class="fas fa-lock"></i> Acesso Restrito</h2>
        </div>
        <div id="errorMsg" class="error-msg"></div>
        
        <form id="loginForm">
            <div class="input-group">
                <label>Email</label>
                <input type="email" id="email" name="email" required placeholder="admin@exemplo.com">
            </div>
            <div class="input-group">
                <label>Senha</label>
                <input type="password" id="password" name="password" required placeholder="********">
            </div>
            <button type="submit" class="login-btn" id="loginBtn">Entrar</button>
        </form>
    </div>

    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const btn = document.getElementById('loginBtn');
            const errorDiv = document.getElementById('errorMsg');
            
            btn.disabled = true;
            btn.innerText = 'Autenticando...';
            errorDiv.style.display = 'none';
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    console.log("Login OK. Salvando storage...");
                    // Salvar no LocalStorage como solicitado
                    localStorage.setItem('currentUser', JSON.stringify(data.user));
                    localStorage.setItem('authTime', new Date().toISOString());
                    
                    console.log("Redirecionando para home...");
                    // Redirecionar
                    window.location.replace('/');
                } else {
                    errorDiv.innerText = data.message || 'Erro no login';
                    errorDiv.style.display = 'block';
                    btn.disabled = false;
                    btn.innerText = 'Entrar';
                }
            } catch (err) {
                console.error(err);
                errorDiv.innerText = 'Erro de conexão';
                errorDiv.style.display = 'block';
                btn.disabled = false;
                btn.innerText = 'Entrar';
            }
        });
        
        // Limpar storage se estiver na tela de login (logout implícito)
        localStorage.removeItem('currentUser');
    </script>
</body>
</html>'''
    return render_template_string(login_html)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return '''
    <script>
        localStorage.removeItem('currentUser');
        window.location.href = '/login';
    </script>
    '''

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de health check"""
    status = {
        'service': 'ExtractBrowser EC2',
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'dependencies': {
            's3': s3_manager is not None,
            's3_bucket': s3_manager.test_connection() if s3_manager else False,
            'pdf_libs': check_pdf_dependencies(),
            'ai_service': ai_service is not None,
            'openai_available': ai_service.openai_available if ai_service else False
        },
        'config': {
            'bucket': S3_BUCKET,
            'region': AWS_REGION,
            'port': PORT
        }
    }
    
    # Adicionar informações detalhadas
    if s3_manager:
        status['bucket_files'] = len(s3_manager.list_files(max_keys=10))
    
    return jsonify(status)

@app.route('/upload', methods=['POST'])
@login_required
def upload_document():
    """Endpoint para upload de documentos"""
    try:
        start_time = time.time()
        
        # Lazy initialization para garantir que serviços estejam disponíveis
        global s3_manager, ai_service
        if s3_manager is None:
            logger.info("⚠️ S3Manager não inicializado. Tentando inicializar agora...")
            init_s3_manager()
            
        if ai_service is None:
            logger.info("⚠️ AIService não inicializado. Tentando inicializar agora...")
            init_ai_service()
        
        # Verificar se há arquivo no request
        if not request.files and not request.json:
            return jsonify(create_standardized_response(
                success=False,
                message="Nenhum arquivo enviado"
            )), 400
        
        # Processar arquivo do form-data ou JSON
        if request.files and 'file' in request.files:
            file = request.files['file']
            filename = file.filename
            file_content = file.read()
            document_type = request.form.get('document_type', 'generic')
        elif request.json:
            data = request.json
            file_content = base64.b64decode(data.get('file_content', ''))
            filename = data.get('filename', 'document.pdf')
            document_type = data.get('document_type', 'generic')
        else:
            return jsonify(create_standardized_response(
                success=False,
                message="Formato de dados inválido"
            )), 400
        
        if not file_content:
            return jsonify(create_standardized_response(
                success=False,
                message="Arquivo vazio"
            )), 400
        
        if document_type == 'generic':
            # Auto-detectar tipo pelo nome do arquivo (regra simples)
            fname = filename.lower()
            if 'antt' in fname:
                document_type = 'ANTT'
            elif 'cnh' in fname:
                document_type = 'CNH'
            elif 'cnpj' in fname or 'dados' in fname or 'cadastrais' in fname:
                document_type = 'CNPJ'
            elif 'conta' in fname or 'comprovante' in fname or 'fatura' in fname:
                document_type = 'RESIDENCIA'
            elif 'veiculo' in fname or 'crv' in fname or 'crlv' in fname:
                document_type = 'VEICULO'
        
        logger.info(f"📄 Processando arquivo: {filename} ({len(file_content)} bytes) - Tipo: {document_type}")
        
        # Verificar tipo de arquivo
        is_pdf = filename.lower().endswith('.pdf')
        is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg'))
        
        if not (is_pdf or is_image):
            return jsonify(create_standardized_response(
                success=False,
                message="Tipo de arquivo não suportado. Use PDF, PNG, JPG ou JPEG."
            )), 400
        
        # Validar PDF se necessário
        if is_pdf:
            is_valid, validation_msg = validate_pdf(file_content)
            if not is_valid:
                return jsonify(create_standardized_response(
                    success=False,
                    message=f"PDF inválido: {validation_msg}"
                )), 400
        
        # Upload do arquivo original
        try:
            original_key = s3_manager.upload_file(
                file_content, 
                filename, 
                folder="original_files",
                content_type="application/pdf" if is_pdf else "image/jpeg"
            )
        except Exception as e:
            logger.error(f"❌ Erro crítico no upload S3: {str(e)}")
            return jsonify(create_standardized_response(
                success=False,
                message=f"Erro interno no upload S3: {str(e)}"
            )), 500
        
        if not original_key:
            logger.error("❌ s3_manager.upload_file retornou None")
            return jsonify(create_standardized_response(
                success=False,
                message="Falha ao salvar arquivo no S3 (retornou vazio)"
            )), 500
        
        result = {
            'success': True,
            'filename': filename,
            'size': len(file_content),
            'document_type': document_type,
            'original_key': original_key,
            'original_url': s3_manager.get_public_url(original_key),
            'is_pdf': is_pdf,
            'is_image': is_image
        }
        
        # Processar PDF - extrair preview e informações
        if is_pdf:
            logger.info("🎨 Extraindo preview do PDF...")
            
            # Extrair informações do PDF
            pdf_info = get_pdf_info(file_content)
            result['pdf_info'] = pdf_info
            
            # Extrair preview da primeira página
            preview_bytes = extract_pdf_preview(file_content, dpi=150)
            
            if preview_bytes:
                # Upload do preview
                preview_filename = f"preview_{filename.replace('.pdf', '.png')}"
                preview_key = s3_manager.upload_file(
                    preview_bytes,
                    preview_filename,
                    folder="preview_images",
                    content_type="image/png"
                )
                
                if preview_key:
                    result['preview_key'] = preview_key
                    result['preview_url'] = s3_manager.get_public_url(preview_key)
                    logger.info(f"✅ Preview salvo: {preview_key}")
                else:
                    logger.error("❌ Erro ao salvar preview no S3")
            else:
                logger.error("❌ Erro ao extrair preview do PDF")
            
            # Extrair texto completo do PDF
            # Extrair texto completo do PDF (todas as páginas)
            text_content = extract_text_from_pdf(file_content, max_pages=None)
            if text_content:
                result['extracted_text'] = text_content[:1000] + "..." if len(text_content) > 1000 else text_content
                
                # Estruturar dados com IA se disponível
                if ai_service and text_content:
                    logger.info("🤖 Estruturando dados com IA...")
                    structured_result = ai_service.structure_data(text_content, document_type)
                    
                    # Adicionar dados estruturados ao resultado
                    # structured_result['data'] é o wrapper {data, usage, confidence}
                    ai_wrapper = structured_result.get('data', {})
                    
                    # Verificar se é o formato antigo ou novo
                    if 'usage' in ai_wrapper:
                        result['structured_data'] = ai_wrapper.get('data', {})
                        result['ai_usage'] = ai_wrapper.get('usage', {})
                        result['ai_confidence'] = ai_wrapper.get('confidence', 0.0)
                    else:
                        # Fallback seguro para evitar erro de chave
                        if isinstance(ai_wrapper, dict) and 'data' in ai_wrapper:
                             # Formato wrapper mas sem usage?
                             result['structured_data'] = ai_wrapper.get('data', {})
                        else:
                             # Formato direto (apenas os dados)
                             result['structured_data'] = ai_wrapper
                        
                        result['ai_usage'] = {}
                        # Tenta pegar confiança do wrapper ou dos próprios dados
                        if isinstance(ai_wrapper, dict):
                            result['ai_confidence'] = ai_wrapper.get('confidence', 0.0)
                        else:
                            result['ai_confidence'] = 0.0
                    
                    result['ai_processing_time_ms'] = structured_result['processing_time_ms']
                    
                    if structured_result['success']:
                        logger.info(f"✅ Dados estruturados com confiança: {result['ai_confidence']}")
                    else:
                        result['ai_error'] = "Falha na estruturação de dados"
                        logger.warning(f"❌ Falha na estruturação")
                else:
                    result['structured_data'] = {
                        "success": False,
                        "data": {},
                        "confidence": 0.0
                    }
                    result['ai_processing_time_ms'] = 0
                    if not ai_service:
                        result['ai_error'] = "Serviço de IA não disponível"
        
        # Processar IMAGEM - extrair texto via OCR e estruturar dados
        elif is_image:
            logger.info("🔍 Processando imagem com OCR...")
            
            # A imagem original já foi salva, usar como preview também
            result['preview_key'] = original_key
            result['preview_url'] = s3_manager.get_public_url(original_key)
            
            # Extrair texto da imagem usando AWS Textract
            text_content = extract_text_from_image(file_content)
            if text_content:
                result['extracted_text'] = text_content[:1000] + "..." if len(text_content) > 1000 else text_content
                logger.info(f"📝 Texto extraído da imagem: {len(text_content)} caracteres")
                
                # Estruturar dados com IA se disponível
                if ai_service and text_content:
                    logger.info("🤖 Estruturando dados com IA...")
                    structured_result = ai_service.structure_data(text_content, document_type)
                    
                    # Adicionar dados estruturados ao resultado
                    ai_wrapper = structured_result.get('data', {})
                    
                    if 'usage' in ai_wrapper:
                        result['structured_data'] = ai_wrapper.get('data', {})
                        result['ai_usage'] = ai_wrapper.get('usage', {})
                        result['ai_confidence'] = ai_wrapper.get('confidence', 0.0)
                    else:
                        # Fallback seguro para evitar erro de chave
                        if isinstance(ai_wrapper, dict) and 'data' in ai_wrapper:
                             # Formato wrapper mas sem usage?
                             result['structured_data'] = ai_wrapper.get('data', {})
                        else:
                             # Formato direto (apenas os dados)
                             result['structured_data'] = ai_wrapper
                        
                        result['ai_usage'] = {}
                         # Tenta pegar confiança do wrapper ou dos próprios dados
                        if isinstance(ai_wrapper, dict):
                            result['ai_confidence'] = ai_wrapper.get('confidence', 0.0)
                        else:
                            result['ai_confidence'] = 0.0

                    result['ai_processing_time_ms'] = structured_result['processing_time_ms']
                    
                    if structured_result['success']:
                        logger.info(f"✅ Dados estruturados com confiança: {result['ai_confidence']}")
                    else:
                        result['ai_error'] = "Falha na estruturação de dados"
                        logger.warning(f"❌ Falha na estruturação")
                else:
                    result['structured_data'] = {
                        "success": False,
                        "data": {},
                        "confidence": 0.0
                    }
                    result['ai_processing_time_ms'] = 0
                    if not ai_service:
                        result['ai_error'] = "Serviço de IA não disponível"
            else:
                logger.warning("⚠️ Não foi possível extrair texto da imagem")
                result['extracted_text'] = ""
                result['structured_data'] = {
                    "success": False,
                    "data": {},
                    "confidence": 0.0
                }
                result['ai_processing_time_ms'] = 0
                result['ai_error'] = "Falha na extração de texto da imagem"
        
        processing_time = int((time.time() - start_time) * 1000)
        result['processing_time_ms'] = processing_time
        result['timestamp'] = datetime.now().isoformat()
        
        # Salvar LOG no banco de dados
        try:
            log_entry = ExtractionLog(
                filename=filename,
                document_type=document_type,
                s3_original_key=result.get('original_key'),
                s3_preview_key=result.get('preview_key'),
                s3_original_url=result.get('original_url'),
                s3_preview_url=result.get('preview_url'),
                model_name=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                input_tokens=result.get('ai_usage', {}).get('input_tokens', 0),
                output_tokens=result.get('ai_usage', {}).get('output_tokens', 0),
                total_tokens=result.get('ai_usage', {}).get('total_tokens', 0),
                confidence=result.get('ai_confidence', 0.0),
                structured_data=json.dumps(result.get('structured_data', {}), ensure_ascii=False),
                processing_time_ms=processing_time,
                status='success'
            )
            db.session.add(log_entry)
            db.session.commit()
            logger.info(f"💾 Log salvo no banco de dados: ID {log_entry.id}")
            
        except Exception as db_error:
            logger.error(f"❌ Erro ao salvar log no banco: {db_error}")

        # Padronizar resposta conforme formato especificado
        standardized_response = create_standardized_response(
            success=True,
            message="Documento processado com sucesso",
            document_type=document_type,
            structured_data=result.get('structured_data', {}),
            processing_time_ms=processing_time,
            additional_data={
                'filename': result.get('filename'),
                'size': result.get('size'),
                'original_key': result.get('original_key'),
                'original_url': result.get('original_url'),
                'preview_key': result.get('preview_key'),
                'preview_url': result.get('preview_url'),
                'extracted_text': result.get('extracted_text'),
                'is_pdf': result.get('is_pdf'),
                'is_image': result.get('is_image'),
                'pdf_info': result.get('pdf_info'),
                'ai_confidence': result.get('ai_confidence', 0.0),
                'timestamp': result.get('timestamp')
            }
        )
        
        logger.info(f"✅ Documento processado em {processing_time}ms")
        return jsonify(standardized_response)
        
    except Exception as e:
        logger.error(f"❌ Erro no upload: {e}")
        return jsonify(create_standardized_response(
            success=False,
            message=f"Erro interno: {str(e)}"
        )), 500

@app.route('/view/<path:s3_key>')
def view_document(s3_key):
    """Endpoint para visualizar documentos do S3"""
    try:
        logger.info(f"📥 Solicitação de visualização: {s3_key}")
        
        # Baixar arquivo do S3
        file_content = s3_manager.download_file(s3_key)
        
        if not file_content:
            return jsonify(create_standardized_response(
                success=False,
                message="Arquivo não encontrado"
            )), 404
        
        # Determinar content type
        if s3_key.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        elif s3_key.lower().endswith('.png'):
            content_type = 'image/png'
        elif s3_key.lower().endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        else:
            content_type = 'application/octet-stream'
        
        # Criar resposta com arquivo
        from flask import Response
        response = Response(file_content, content_type=content_type)
        
        # Headers para visualização inline
        filename = s3_key.split('/')[-1]  # Apenas o nome do arquivo
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache 1 hora
        
        logger.info(f"✅ Arquivo enviado: {filename} ({len(file_content)} bytes)")
        return response
        
    except Exception as e:
        logger.error(f"❌ Erro na visualização: {e}")
        return jsonify(create_standardized_response(
            success=False,
            message=f"Erro interno: {str(e)}"
        )), 500

@app.route('/history')
@login_required
def history():
    """Página de histórico de extrações com filtros e paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    doc_type = request.args.get('type')
    status = request.args.get('status')
    
    query = ExtractionLog.query.order_by(ExtractionLog.created_at.desc())
    
    if doc_type:
        query = query.filter(ExtractionLog.document_type == doc_type)
    if status:
        query = query.filter(ExtractionLog.status == status)
        
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    # HTML do Histórico
    html = '''<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Histórico - ExtractBrowser</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f6f9; color: #333; margin: 0; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 15px 40px; display: flex; justify-content: space-between; align-items: center; color: white; }
        .navbar h1 { font-size: 1.5em; margin: 0; }
        .nav-links a { color: white; text-decoration: none; margin-left: 20px; font-weight: 500; }
        .container { max-width: 1200px; margin: 30px auto; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .filters { display: flex; gap: 15px; margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee; }
        select, button { padding: 10px; border-radius: 5px; border: 1px solid #ddd; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: #666; font-weight: 600; }
        .badge { padding: 5px 10px; border-radius: 15px; font-size: 0.8em; font-weight: 600; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .badge-info { background: #d1ecf1; color: #0c5460; }
        .pagination { display: flex; justify-content: center; margin-top: 30px; gap: 10px; }
        .pagination a { padding: 8px 12px; border: 1px solid #ddd; text-decoration: none; color: #667eea; border-radius: 5px; }
        .pagination a.active { background: #667eea; color: white; border-color: #667eea; }
        .tokens { font-family: monospace; color: #666; }
        .clickable-row { cursor: pointer; transition: background 0.1s; }
        .clickable-row:hover { background-color: #f1f1f1; }
        
        /* Modal Styles */
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .modal-content { background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 800px; max-height: 80vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
        .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: black; }
        pre { background: #f4f6f9; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .key-value-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-top: 15px; }
        .kv-item { background: #f8f9fa; padding: 10px; border-radius: 5px; border: 1px solid #eee; }
        .kv-label { font-size: 0.8em; color: #666; font-weight: 600; text-transform: uppercase; margin-bottom: 3px; }
        .kv-value { font-size: 1em; color: #333; word-break: break-word; }
    </style>
</head>
<body>
    <nav class="navbar">
        <h1><i class="fas fa-history"></i> Histórico de Extrações</h1>
        <div class="nav-links">
            <a href="{{ url_for('index') }}"><i class="fas fa-upload"></i> Nova Extração</a>
            <a href="{{ url_for('logout') }}"><i class="fas fa-sign-out-alt"></i> Sair</a>
        </div>
    </nav>
    
    <div class="container">
        <form class="filters" method="GET">
            <select name="type" onchange="this.form.submit()">
                <option value="">Todos os Tipos</option>
                <option value="ANTT" {% if request.args.get('type') == 'ANTT' %}selected{% endif %}>ANTT (Certificado/Extrato)</option>
                <option value="CNH" {% if request.args.get('type') == 'CNH' %}selected{% endif %}>CNH (Habilitação)</option>
                <option value="CNPJ" {% if request.args.get('type') == 'CNPJ' %}selected{% endif %}>CNPJ (Cartão/Dados)</option>
                <option value="VEICULO" {% if request.args.get('type') == 'VEICULO' %}selected{% endif %}>Veículo (CRV/CRLV)</option>
                <option value="RESIDENCIA" {% if request.args.get('type') == 'RESIDENCIA' %}selected{% endif %}>Residência (Contas)</option>
                <option value="GENERIC" {% if request.args.get('type') == 'GENERIC' %}selected{% endif %}>Genérico/Outros</option>
            </select>
            <select name="status" onchange="this.form.submit()">
                <option value="">Todos os Status</option>
                <option value="success" {% if request.args.get('status') == 'success' %}selected{% endif %}>Sucesso</option>
                <option value="error" {% if request.args.get('status') == 'error' %}selected{% endif %}>Erro</option>
            </select>
            <a href="{{ url_for('history') }}" style="padding: 10px; color: #666; text-decoration: none;">Limpar</a>
        </form>

        <table>
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Arquivo</th>
                    <th>Tipo</th>
                    <th>Confiança</th>
                    <th>Tokens (In/Out/Total)</th>
                    <th>Links</th>
                </tr>
            </thead>
            <tbody>
                {% for log in logs %}
                <tr class="clickable-row" onclick="openModal('{{ log.id }}')">
                    <td>{{ log.created_at.strftime('%d/%m/%Y %H:%M') }}</td>
                    <td>{{ log.filename }}</td>
                    <td><span class="badge badge-info">{{ log.document_type }}</span></td>
                    <td>
                        {% if log.confidence > 0.8 %}
                            <span class="badge badge-success">{{ "%.1f"|format(log.confidence * 100) }}%</span>
                        {% else %}
                            <span class="badge badge-warning">{{ "%.1f"|format(log.confidence * 100) }}%</span>
                        {% endif %}
                    </td>
                    <td class="tokens">{{ log.input_tokens }} / {{ log.output_tokens }} / <strong>{{ log.total_tokens }}</strong></td>
                    <td onclick="event.stopPropagation()">
                        {% if log.s3_preview_url %}
                            <a href="{{ log.s3_preview_url }}" target="_blank" title="Ver Preview"><i class="fas fa-image"></i></a>
                        {% endif %}
                        {% if log.s3_original_url %}
                            <a href="{{ log.s3_original_url }}" target="_blank" title="Ver Original" style="margin-left: 10px;"><i class="fas fa-file-pdf"></i></a>
                        {% endif %}
                    </td>
                </tr>
                
                <!-- Hidden Data for Modal -->
                <script>
                    window.logData_{{ log.id }} = {{ log.structured_data|default('{}')|safe }};
                </script>
                {% else %}
                <tr>
                    <td colspan="6" style="text-align: center;">Nenhum registro encontrado.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="pagination">
            {% if pagination.has_prev %}
                <a href="{{ url_for('history', page=pagination.prev_num, **request.args) }}">&laquo; Anterior</a>
            {% endif %}
            
            {% for p in pagination.iter_pages() %}
                {% if p %}
                    {% if p == pagination.page %}
                        <a href="#" class="active">{{ p }}</a>
                    {% else %}
                        <a href="{{ url_for('history', page=p, **request.args) }}">{{ p }}</a>
                    {% endif %}
                {% else %}
                    <span>...</span>
                {% endif %}
            {% endfor %}

            {% if pagination.has_next %}
                <a href="{{ url_for('history', page=pagination.next_num, **request.args) }}">Próxima &raquo;</a>
            {% endif %}
        </div>
    </div>

    <!-- Modal -->
    <div id="detailsModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <h2><i class="fas fa-info-circle"></i> Detalhes da Extração</h2>
            <div id="modalContent"></div>
            <h3>JSON Bruto</h3>
            <pre id="modalJson"></pre>
        </div>
    </div>

    <script>
        function openModal(id) {
            const data = window['logData_' + id];
            const modal = document.getElementById('detailsModal');
            const contentDiv = document.getElementById('modalContent');
            const jsonPre = document.getElementById('modalJson');
            
            // Gerar Visualização Gride
            let html = '<div class="key-value-grid">';
            for (const [key, value] of Object.entries(data)) {
                if (typeof value !== 'object') {
                    html += `
                        <div class="kv-item">
                            <div class="kv-label">${key.replace(/_/g, ' ')}</div>
                            <div class="kv-value">${value}</div>
                        </div>
                    `;
                }
            }
            html += '</div>';
            
            contentDiv.innerHTML = html;
            jsonPre.textContent = JSON.stringify(data, null, 2);
            modal.style.display = "block";
        }

        function closeModal() {
            document.getElementById('detailsModal').style.display = "none";
        }

        window.onclick = function(event) {
            const modal = document.getElementById('detailsModal');
            if (event.target == modal) {
                modal.style.display = "none";
            }
        }
    </script>
</body>
</html>'''
    return render_template_string(html, logs=logs, pagination=pagination)

@app.route('/files')
def list_files():
    """Lista arquivos no bucket"""
    try:
        files = s3_manager.list_files(max_keys=50)
        return jsonify(create_standardized_response(
            success=True,
            message="Arquivos listados com sucesso",
            additional_data={
                'files': files,
                'count': len(files)
            }
        ))
    except Exception as e:
        logger.error(f"❌ Erro ao listar arquivos: {e}")
        return jsonify(create_standardized_response(
            success=False,
            message=f"Erro interno: {str(e)}"
        )), 500

@app.route('/')
@login_required
def index():
    """Página inicial com interface igual ao projeto anterior"""
    html = '''<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema OCR Inteligente - Extração de Documentos</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }

        .main-content {
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            overflow: hidden;
        }

        .upload-card {
            padding: 40px;
            text-align: center;
        }

        .upload-header h2 {
            color: #667eea;
            margin-bottom: 10px;
        }

        .upload-header p {
            color: #666;
            margin-bottom: 30px;
        }

        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 15px;
            padding: 60px 20px;
            margin: 30px 0;
            transition: all 0.3s ease;
            cursor: pointer;
            background: #fafafa;
        }

        .upload-area:hover, .upload-area.dragover {
            border-color: #667eea;
            background: #f0f4ff;
            transform: translateY(-2px);
        }

        .upload-icon {
            font-size: 4em;
            color: #667eea;
            margin-bottom: 20px;
        }

        .upload-text {
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }

        .upload-formats {
            color: #666;
            font-size: 0.9em;
        }

        .document-type-section {
            margin: 30px 0;
        }

        .document-type-section label {
            display: block;
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
        }

        .document-type-section select {
            width: 100%;
            max-width: 400px;
            padding: 12px 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            background: white;
            cursor: pointer;
        }

        .process-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 25px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 20px;
        }

        .process-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }

        .process-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .status-section {
            padding: 20px 40px;
            background: #f8f9fa;
            border-top: 1px solid #eee;
        }

        .status {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-weight: 600;
        }

        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .status.loading {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .progress-section {
            padding: 30px 40px;
            background: #f8f9fa;
            text-align: center;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #eee;
            border-radius: 4px;
            overflow: hidden;
            margin: 20px 0;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
            width: 0%;
        }

        .results-section {
            padding: 40px;
        }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }

        .results-header h3 {
            color: #667eea;
        }

        .confidence-badge {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: 600;
        }

        .tabs {
            display: flex;
            border-bottom: 2px solid #eee;
            margin-bottom: 30px;
        }

        .tab-btn {
            background: none;
            border: none;
            padding: 15px 20px;
            cursor: pointer;
            font-weight: 600;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
        }

        .tab-btn.active, .tab-btn:hover {
            color: #667eea;
            border-bottom-color: #667eea;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .json-display {
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .footer {
            text-align: center;
            color: white;
            margin-top: 40px;
            opacity: 0.8;
        }

        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .upload-card {
                padding: 20px;
            }
            
            .results-header {
                flex-direction: column;
                gap: 15px;
            }
            
            .tabs {
                flex-wrap: wrap;
            }
            
            .tab-btn {
                flex: 1;
                min-width: 120px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-content">
                <h1><i class="fas fa-file-text"></i> Sistema OCR Inteligente</h1>
                <p>Extração e estruturação de dados de documentos brasileiros</p>
                <div style="margin-top: 15px;">
                    <span id="welcomeMsg" style="color: white; margin-right: 20px; font-weight: 500;"></span>
                    <a href="/history" style="color: white; text-decoration: none; margin-right: 20px; font-weight: 500;"><i class="fas fa-history"></i> Ver Histórico</a>
                    <a href="/logout" style="color: white; text-decoration: none; font-weight: 500;"><i class="fas fa-sign-out-alt"></i> Sair</a>
                </div>
            </div>
        </header>

        <script>
            // Validar sessão local
            const user = JSON.parse(localStorage.getItem('currentUser'));
            if (!user) {
                // Se não tem user no storage, mas acessou index, algo está estranho (ou session cookie existe mas storage não)
                // Vamos forçar o storage se possível ou apenas ignorar
                console.log("Sessão ativa via Cookie, mas LocalStorage vazio.");
            } else {
                document.getElementById('welcomeMsg').innerText = 'Olá, ' + (user.name || user.email);
            }
        </script>

        <main class="main-content">
            <!-- Upload Section -->
            <section class="upload-section">
                <div class="upload-card">
                    <div class="upload-header">
                        <h2><i class="fas fa-cloud-upload-alt"></i> Enviar Documento</h2>
                        <p>Arraste ou clique para selecionar seu documento</p>
                    </div>
                    
                    <div class="upload-area" id="uploadArea">
                        <div class="upload-content">
                            <i class="fas fa-file-plus upload-icon"></i>
                            <p class="upload-text">Clique aqui ou arraste o arquivo</p>
                            <p class="upload-formats">PDF, JPG, PNG (máx. 10MB)</p>
                        </div>
                        <input type="file" id="fileInput" accept=".pdf,.jpg,.jpeg,.png" hidden>
                    </div>
                    
                    <div class="document-type-section">
                        <label for="documentType">Tipo de Documento (opcional):</label>
                        <select id="documentType">
                            <option value="">Detectar automaticamente</option>
                            <option value="ANTT">ANTT (Certificado/Extrato)</option>
                            <option value="CNH">CNH - Carteira Nacional de Habilitação</option>
                            <option value="CNPJ">CNPJ - Cadastro Nacional da Pessoa Jurídica</option>
                            <option value="VEICULO">Veículo (CRV/CRLV/Ficha)</option>
                            <option value="RESIDENCIA">Comprovante de Residência (Luz/Água/Etc)</option>
                        </select>
                    </div>
                    
                    <button id="processBtn" class="process-btn" disabled>
                        <i class="fas fa-cogs"></i>
                        Processar Documento
                    </button>
                </div>
            </section>

            <!-- Status Section -->
            <section class="status-section">
                <div id="status" class="status loading">
                    <i class="fas fa-spinner fa-spin"></i> Carregando status do sistema...
                </div>
            </section>

            <!-- Progress Section -->
            <section class="progress-section" id="progressSection" style="display: none;">
                <div class="progress-card">
                    <h3><i class="fas fa-spinner fa-spin"></i> Processando...</h3>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill"></div>
                    </div>
                    <p class="progress-text" id="progressText">Iniciando processamento...</p>
                </div>
            </section>

            <!-- Results Section -->
            <section class="results-section" id="resultsSection" style="display: none;">
                <div class="results-header">
                    <h3><i class="fas fa-check-circle"></i> Dados Extraídos</h3>
                    <div class="confidence-badge" id="confidenceBadge">
                        <i class="fas fa-chart-line"></i>
                        <span id="confidenceText">0%</span>
                    </div>
                </div>
                
                <div class="tabs">
                    <button class="tab-btn active" data-tab="structured">
                        <i class="fas fa-list"></i> Dados Estruturados
                    </button>
                    <button class="tab-btn" data-tab="json">
                        <i class="fas fa-code"></i> JSON Completo
                    </button>
                    <button class="tab-btn" data-tab="preview">
                        <i class="fas fa-eye"></i> Preview
                    </button>
                </div>
                
                <div id="structured" class="tab-content active">
                    <div id="structuredData"></div>
                </div>
                
                <div id="json" class="tab-content">
                    <div id="jsonData" class="json-display"></div>
                </div>
                
                <div id="preview" class="tab-content">
                    <div id="previewData"></div>
                </div>
            </section>
        </main>

        <footer class="footer">
            <p>&copy; 2024 Sistema OCR Inteligente. Powered by AWS e OpenAI.</p>
        </footer>
    </div>

    <script>
        let selectedFile = null;
        let currentResult = null;

        // Verificar status da API
        async function checkStatus() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                
                const statusEl = document.getElementById('status');
                const deps = data.dependencies;
                
                let statusHtml = `
                    <i class="fas fa-check-circle"></i>
                    <strong>Status:</strong> ${data.status} | 
                    <strong>S3:</strong> ${deps.s3 ? '✅' : '❌'} | 
                    <strong>PDF:</strong> ${deps.pdf_libs ? '✅' : '❌'} | 
                    <strong>IA:</strong> ${deps.ai_service ? '✅' : '❌'}
                `;
                
                if (deps.openai_available) {
                    statusHtml += ' | <strong>OpenAI:</strong> ✅';
                } else {
                    statusHtml += ' | <strong>OpenAI:</strong> ❌';
                }
                
                statusEl.innerHTML = statusHtml;
                statusEl.className = 'status success';
            } catch (error) {
                document.getElementById('status').innerHTML = 
                    '<i class="fas fa-exclamation-triangle"></i> Erro de conexão com o servidor';
                document.getElementById('status').className = 'status error';
            }
        }

        // Setup drag and drop
        function setupDragAndDrop() {
            const uploadArea = document.getElementById('uploadArea');
            
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileSelect(files[0]);
                }
            });
            
            uploadArea.addEventListener('click', () => {
                document.getElementById('fileInput').click();
            });
        }

        // File input change
        document.getElementById('fileInput').addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });

        // Handle file selection
        function handleFileSelect(file) {
            selectedFile = file;
            document.getElementById('processBtn').disabled = false;
            
            // Update upload area
            const uploadArea = document.getElementById('uploadArea');
            uploadArea.innerHTML = `
                <div class="upload-content">
                    <i class="fas fa-file-check upload-icon" style="color: #28a745;"></i>
                    <p class="upload-text">${file.name}</p>
                    <p class="upload-formats">${formatFileSize(file.size)}</p>
                </div>
            `;
        }

        // Process document
        document.getElementById('processBtn').addEventListener('click', async () => {
            if (!selectedFile) return;
            
            const documentType = document.getElementById('documentType').value;
            await processDocument(selectedFile, documentType);
        });

        // Process document function
        async function processDocument(file, documentType) {
            try {
                showProgress('Enviando arquivo...', 10);
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('document_type', documentType || 'generic');
                
                showProgress('Processando documento...', 30);
                
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                showProgress('Analisando resultados...', 70);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                showProgress('Concluído!', 100);
                
                if (result.success) {
                    currentResult = result;
                    showResults(result);
                } else {
                    throw new Error(result.message || 'Erro no processamento');
                }
                
            } catch (error) {
                console.error('Erro no processamento:', error);
                showError(`Erro: ${error.message}`);
                hideProgress();
            }
        }

        // Show progress
        function showProgress(text, percent) {
            document.getElementById('progressSection').style.display = 'block';
            document.getElementById('progressText').textContent = text;
            document.getElementById('progressFill').style.width = `${percent}%`;
            
            if (percent >= 100) {
                setTimeout(hideProgress, 1000);
            }
        }

        // Hide progress
        function hideProgress() {
            document.getElementById('progressSection').style.display = 'none';
        }

        // Show error
        function showError(message) {
            const statusEl = document.getElementById('status');
            statusEl.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
            statusEl.className = 'status error';
        }

        // Show results
        function showResults(result) {
            document.getElementById('resultsSection').style.display = 'block';
            
            // Extrair dados da nova estrutura padronizada
            const data = result.data || {};
            const structuredData = data.data || {};
            
            // Update confidence
            let confidence = 0;
            if (data.ai_confidence) {
                confidence = Math.round(data.ai_confidence * 100);
            }
            document.getElementById('confidenceText').textContent = `${confidence}%`;
            
            // Show structured data
            if (structuredData && Object.keys(structuredData).length > 0) {
                document.getElementById('structuredData').innerHTML = formatStructuredData(structuredData);
            } else {
                document.getElementById('structuredData').innerHTML = '<p>Dados estruturados não disponíveis</p>';
            }
            
            // Show JSON
            document.getElementById('jsonData').textContent = JSON.stringify(result, null, 2);
            
            // Show preview
            if (data.preview_url) {
                document.getElementById('previewData').innerHTML = `
                    <img src="${data.preview_url}" style="max-width: 100%; border-radius: 8px;" alt="Preview">
                `;
            } else if (data.preview_key) {
                document.getElementById('previewData').innerHTML = `
                    <img src="/view/${data.preview_key}" style="max-width: 100%; border-radius: 8px;" alt="Preview">
                `;
            } else {
                document.getElementById('previewData').innerHTML = '<p>Preview não disponível</p>';
            }
        }

        // Format structured data
        function formatStructuredData(data) {
            let html = '<div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">';
            
            for (const [key, value] of Object.entries(data)) {
                if (value && typeof value === 'object' && !Array.isArray(value)) {
                    html += `<h4>${key}:</h4><ul>`;
                    for (const [subKey, subValue] of Object.entries(value)) {
                        if (subValue) {
                            html += `<li><strong>${subKey}:</strong> ${subValue}</li>`;
                        }
                    }
                    html += '</ul>';
                } else if (value) {
                    html += `<p><strong>${key}:</strong> ${value}</p>`;
                }
            }
            
            html += '</div>';
            return html;
        }

        // Tab functionality
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Remove active from all
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                // Add active to clicked
                btn.classList.add('active');
                document.getElementById(btn.dataset.tab).classList.add('active');
            });
        });

        // Format file size
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            checkStatus();
            setupDragAndDrop();
        });
    </script>
</body>
</html>'''
    return html

# Inicializar serviços na carga do módulo (para Gunicorn)
logger.info("🚀 Inicializando serviços do ExtractBrowser...")

if not init_s3_manager():
    logger.error("❌ Falha ao inicializar S3Manager - servidor pode não funcionar corretamente")

if not init_ai_service():
    logger.warning("⚠️ Serviço de IA não disponível - estruturação de dados não funcionará")

if not check_pdf_dependencies():
    logger.error("❌ Dependências PDF não disponíveis - extração de preview não funcionará")

# Inicializar banco de dados
init_db()

if __name__ == '__main__':
    logger.info(f"🌐 Servidor rodando na porta {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
