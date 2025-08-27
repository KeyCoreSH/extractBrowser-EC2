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

# Gerenciador S3 e Serviço de IA
s3_manager = None
ai_service = None

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
def upload_document():
    """Endpoint para upload de documentos"""
    try:
        start_time = time.time()
        
        # Verificar se há arquivo no request
        if not request.files and not request.json:
            return jsonify({
                'success': False,
                'message': 'Nenhum arquivo enviado'
            }), 400
        
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
            return jsonify({
                'success': False,
                'message': 'Formato de dados inválido'
            }), 400
        
        if not file_content:
            return jsonify({
                'success': False,
                'message': 'Arquivo vazio'
            }), 400
        
        logger.info(f"📄 Processando arquivo: {filename} ({len(file_content)} bytes)")
        
        # Verificar tipo de arquivo
        is_pdf = filename.lower().endswith('.pdf')
        is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg'))
        
        if not (is_pdf or is_image):
            return jsonify({
                'success': False,
                'message': 'Tipo de arquivo não suportado. Use PDF, PNG, JPG ou JPEG.'
            }), 400
        
        # Validar PDF se necessário
        if is_pdf:
            is_valid, validation_msg = validate_pdf(file_content)
            if not is_valid:
                return jsonify({
                    'success': False,
                    'message': f'PDF inválido: {validation_msg}'
                }), 400
        
        # Upload do arquivo original
        original_key = s3_manager.upload_file(
            file_content, 
            filename, 
            folder="original_files",
            content_type="application/pdf" if is_pdf else "image/jpeg"
        )
        
        if not original_key:
            return jsonify({
                'success': False,
                'message': 'Erro ao salvar arquivo no S3'
            }), 500
        
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
            text_content = extract_text_from_pdf(file_content, max_pages=3)
            if text_content:
                result['extracted_text'] = text_content[:1000] + "..." if len(text_content) > 1000 else text_content
                
                # Estruturar dados com IA se disponível
                if ai_service and text_content:
                    logger.info("🤖 Estruturando dados com IA...")
                    structured_result = ai_service.structure_data(text_content, document_type)
                    
                    if structured_result['success']:
                        result['structured_data'] = structured_result['data']
                        result['ai_confidence'] = structured_result['confidence']
                        result['ai_metadata'] = structured_result['metadata']
                        
                        # Validar dados estruturados
                        validation = ai_service.validate_structured_data(
                            structured_result['data'], 
                            document_type
                        )
                        result['validation'] = validation
                        
                        logger.info(f"✅ Dados estruturados com confiança: {structured_result['confidence']}")
                    else:
                        result['structured_data'] = {}
                        result['ai_error'] = structured_result['error']
                        logger.warning(f"❌ Falha na estruturação: {structured_result['error']}")
                else:
                    result['structured_data'] = {}
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
                    
                    if structured_result['success']:
                        result['structured_data'] = structured_result['data']
                        result['ai_confidence'] = structured_result['confidence']
                        result['ai_metadata'] = structured_result['metadata']
                        
                        # Validar dados estruturados
                        validation = ai_service.validate_structured_data(
                            structured_result['data'], 
                            document_type
                        )
                        result['validation'] = validation
                        
                        logger.info(f"✅ Dados estruturados com confiança: {structured_result['confidence']}")
                    else:
                        result['structured_data'] = {}
                        result['ai_error'] = structured_result['error']
                        logger.warning(f"❌ Falha na estruturação: {structured_result['error']}")
                else:
                    result['structured_data'] = {}
                    if not ai_service:
                        result['ai_error'] = "Serviço de IA não disponível"
            else:
                logger.warning("⚠️ Não foi possível extrair texto da imagem")
                result['extracted_text'] = ""
                result['structured_data'] = {}
                result['ai_error'] = "Falha na extração de texto da imagem"
        
        processing_time = int((time.time() - start_time) * 1000)
        result['processing_time_ms'] = processing_time
        result['timestamp'] = datetime.now().isoformat()
        
        logger.info(f"✅ Documento processado em {processing_time}ms")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Erro no upload: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

@app.route('/view/<path:s3_key>')
def view_document(s3_key):
    """Endpoint para visualizar documentos do S3"""
    try:
        logger.info(f"📥 Solicitação de visualização: {s3_key}")
        
        # Baixar arquivo do S3
        file_content = s3_manager.download_file(s3_key)
        
        if not file_content:
            return jsonify({
                'success': False,
                'message': 'Arquivo não encontrado'
            }), 404
        
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
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

@app.route('/files')
def list_files():
    """Lista arquivos no bucket"""
    try:
        files = s3_manager.list_files(max_keys=50)
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        logger.error(f"❌ Erro ao listar arquivos: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        }), 500

@app.route('/')
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
            </div>
        </header>

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
                            <option value="CNH">CNH - Carteira Nacional de Habilitação</option>
                            <option value="CNPJ">CNPJ - Cadastro Nacional da Pessoa Jurídica</option>
                            <option value="CPF">CPF - Cadastro de Pessoas Físicas</option>
                            <option value="CRV">CRV - Certificado de Registro de Veículo</option>
                            <option value="ANTT">ANTT - Agência Nacional de Transportes</option>
                            <option value="FATURA_ENERGIA">Fatura de Energia Elétrica</option>
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
            
            // Update confidence
            const confidence = Math.round((result.ai_confidence || 0) * 100);
            document.getElementById('confidenceText').textContent = `${confidence}%`;
            
            // Show structured data
            if (result.structured_data && Object.keys(result.structured_data).length > 0) {
                document.getElementById('structuredData').innerHTML = formatStructuredData(result.structured_data);
            } else {
                document.getElementById('structuredData').innerHTML = '<p>Dados estruturados não disponíveis</p>';
            }
            
            // Show JSON
            document.getElementById('jsonData').textContent = JSON.stringify(result, null, 2);
            
            // Show preview
            if (result.preview_key) {
                document.getElementById('previewData').innerHTML = `
                    <img src="/view/${result.preview_key}" style="max-width: 100%; border-radius: 8px;" alt="Preview">
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

if __name__ == '__main__':
    logger.info("🚀 Iniciando ExtractBrowser EC2...")
    
    # Inicializar dependências
    if not init_s3_manager():
        logger.error("❌ Falha ao inicializar S3Manager - servidor pode não funcionar corretamente")
    
    if not init_ai_service():
        logger.warning("⚠️ Serviço de IA não disponível - estruturação de dados não funcionará")
    
    if not check_pdf_dependencies():
        logger.error("❌ Dependências PDF não disponíveis - extração de preview não funcionará")
    
    logger.info(f"🌐 Servidor rodando na porta {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
