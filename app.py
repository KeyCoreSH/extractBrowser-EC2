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
from utils.pdf_extractor import extract_pdf_preview, get_pdf_info, validate_pdf, extract_text_from_pdf
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
            
            # Extrair texto completo
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
    """Página inicial com interface de teste"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ExtractBrowser EC2</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
            .upload-area:hover { border-color: #999; }
            button { background: #007cba; color: white; padding: 10px 20px; border: none; cursor: pointer; }
            button:hover { background: #005a87; }
            .result { margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 5px; }
            #status { margin: 10px 0; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 ExtractBrowser EC2</h1>
            <p>Serviço de extração de documentos rodando no EC2</p>
            
            <div id="status">Status: Carregando...</div>
            
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <p>📁 Clique aqui para selecionar PDF ou imagem</p>
                <input type="file" id="fileInput" style="display: none" accept=".pdf,.png,.jpg,.jpeg">
            </div>
            
            <button onclick="uploadFile()">📤 Enviar Arquivo</button>
            
            <div id="result" class="result" style="display: none;"></div>
        </div>
        
        <script>
            // Verificar status da API
            fetch('/health')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status').innerHTML = 
                        `Status: ${data.status} | S3: ${data.dependencies.s3} | PDF: ${data.dependencies.pdf_libs}`;
                })
                .catch(e => {
                    document.getElementById('status').innerHTML = 'Status: Erro de conexão';
                });
            
            function uploadFile() {
                const fileInput = document.getElementById('fileInput');
                const file = fileInput.files[0];
                
                if (!file) {
                    alert('Selecione um arquivo primeiro');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('document_type', 'generic');
                
                document.getElementById('status').innerHTML = 'Enviando...';
                
                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('result').innerHTML = 
                        `<h3>Resultado:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
                    document.getElementById('status').innerHTML = 
                        data.success ? 'Upload realizado!' : 'Erro no upload';
                })
                .catch(e => {
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('result').innerHTML = `<h3>Erro:</h3><p>${e.message}</p>`;
                    document.getElementById('status').innerHTML = 'Erro de conexão';
                });
            }
        </script>
    </body>
    </html>
    '''
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
