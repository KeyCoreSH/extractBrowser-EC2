#!/usr/bin/env python3
"""
Módulo de extração de PDFs usando PyMuPDF
Implementa extração real de preview da primeira página
"""

import logging
import io
from typing import Optional, Tuple
from PIL import Image
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

def extract_pdf_preview(pdf_bytes: bytes, page_index: int = 0, dpi: int = 150) -> Optional[bytes]:
    """
    Extrai preview real da primeira página do PDF
    
    Args:
        pdf_bytes: Conteúdo do PDF em bytes
        page_index: Índice da página (0 = primeira)
        dpi: Resolução da imagem (padrão 150)
    
    Returns:
        Bytes da imagem PNG ou None se falhar
    """
    try:
        logger.info(f"🔍 Iniciando extração de preview - PDF: {len(pdf_bytes)} bytes, página: {page_index}, DPI: {dpi}")
        
        # Abrir PDF com PyMuPDF
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if len(pdf_doc) == 0:
            logger.error("❌ PDF vazio - nenhuma página encontrada")
            return None
        
        if page_index >= len(pdf_doc):
            logger.warning(f"⚠️ Página {page_index} não existe. PDF tem {len(pdf_doc)} páginas. Usando página 0.")
            page_index = 0
        
        # Obter página
        page = pdf_doc[page_index]
        logger.info(f"📄 Página {page_index} carregada - Dimensões: {page.rect}")
        
        # Calcular matriz de transformação para DPI
        zoom = dpi / 72.0  # 72 DPI é padrão
        matrix = fitz.Matrix(zoom, zoom)
        
        # Renderizar página como imagem
        logger.info(f"🎨 Renderizando página com zoom {zoom:.2f}x (DPI: {dpi})")
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        
        # Converter para PNG
        img_bytes = pix.tobytes("png")
        
        # Fechar documento
        pdf_doc.close()
        
        logger.info(f"✅ Preview extraído com sucesso - {len(img_bytes)} bytes PNG")
        return img_bytes
        
    except Exception as e:
        logger.error(f"❌ Erro na extração de preview: {e}")
        return None

def get_pdf_info(pdf_bytes: bytes) -> dict:
    """
    Obtém informações básicas do PDF
    
    Args:
        pdf_bytes: Conteúdo do PDF em bytes
    
    Returns:
        Dicionário com informações do PDF
    """
    try:
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        info = {
            'page_count': len(pdf_doc),
            'metadata': pdf_doc.metadata,
            'is_encrypted': pdf_doc.needs_pass,
            'is_pdf': pdf_doc.is_pdf,
            'file_size': len(pdf_bytes)
        }
        
        # Obter dimensões da primeira página
        if len(pdf_doc) > 0:
            page = pdf_doc[0]
            rect = page.rect
            info['first_page_size'] = {
                'width': rect.width,
                'height': rect.height,
                'width_mm': rect.width * 25.4 / 72,
                'height_mm': rect.height * 25.4 / 72
            }
        
        pdf_doc.close()
        logger.info(f"📊 Informações PDF obtidas: {info['page_count']} páginas")
        return info
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter informações do PDF: {e}")
        return {'error': str(e)}

def extract_text_from_pdf(pdf_bytes: bytes, max_pages: int = 1) -> str:
    """
    Extrai texto do PDF com lógica inteligente de OCR
    
    Uses OCR fallback if:
    - Direct text is too short (< 50 characters)
    - Contains "assinado" (indicates scanned/signed document)
    
    Args:
        pdf_bytes: Conteúdo do PDF em bytes
        max_pages: Máximo de páginas para extrair texto
    
    Returns:
        Texto extraído
    """
    try:
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        
        pages_to_extract = min(len(pdf_doc), max_pages)
        
        for page_num in range(pages_to_extract):
            page = pdf_doc[page_num]
            
            # 1. Extração de texto direto
            direct_text = page.get_text("text")
            logger.info(f"📄 Página {page_num + 1}: texto direto com {len(direct_text)} caracteres")
            
            # 2. Lógica de decisão para OCR
            is_signed = "assinado" in direct_text.lower()
            is_short = len(direct_text.strip()) < 50
            needs_ocr = is_short or is_signed
            
            if needs_ocr:
                reason = "Palavra 'assinado' detectada" if is_signed else "Texto insuficiente"
                logger.info(f"🔍 {reason} na página {page_num + 1}. Aplicando OCR...")
                
                try:
                    # Renderizar página como imagem para OCR
                    pix = page.get_pixmap(dpi=400)  # Alta resolução para melhor OCR
                    img_bytes = pix.tobytes("png")
                    
                    # Usar AWS Textract para OCR (se disponível)
                    ocr_text = _extract_text_with_textract(img_bytes)
                    
                    if ocr_text and len(ocr_text) > len(direct_text):
                        page_text = ocr_text
                        logger.info(f"✅ OCR produziu mais texto ({len(ocr_text)} chars vs {len(direct_text)} chars)")
                    else:
                        page_text = direct_text
                        logger.info(f"⚠️ Usando texto direto (OCR: {len(ocr_text or '')} chars)")
                        
                except Exception as ocr_error:
                    logger.error(f"❌ Erro no OCR da página {page_num + 1}: {ocr_error}")
                    page_text = direct_text
            else:
                page_text = direct_text
                logger.info(f"📝 Usando texto direto da página {page_num + 1}")
            
            if page_text.strip():
                text_parts.append(f"=== PÁGINA {page_num + 1} ===\n{page_text}\n")
        
        pdf_doc.close()
        
        full_text = "\n".join(text_parts)
        logger.info(f"📝 Texto final extraído de {pages_to_extract} página(s) - {len(full_text)} caracteres")
        return full_text
        
    except Exception as e:
        logger.error(f"❌ Erro na extração de texto: {e}")
        return ""


def _extract_text_with_textract(image_bytes: bytes) -> str:
    """
    Extrai texto de imagem usando AWS Textract
    
    Args:
        image_bytes: Bytes da imagem PNG
    
    Returns:
        Texto extraído via OCR
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        textract = boto3.client('textract')
        
        # Verificar tamanho (Textract tem limite de 5MB)
        if len(image_bytes) > 5 * 1024 * 1024:
            logger.warning(f"⚠️ Imagem muito grande para Textract: {len(image_bytes)} bytes")
            return ""
        
        logger.info(f"🤖 Usando AWS Textract para OCR ({len(image_bytes)} bytes)")
        
        response = textract.detect_document_text(
            Document={'Bytes': image_bytes}
        )
        
        # Extrair texto das linhas detectadas
        text_lines = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_lines.append(block['Text'])
        
        ocr_text = '\n'.join(text_lines)
        logger.info(f"🤖 Textract extraiu {len(ocr_text)} caracteres")
        
        return ocr_text
        
    except ClientError as e:
        logger.error(f"❌ Erro do Textract: {e}")
        return ""
    except Exception as e:
        logger.error(f"❌ Erro geral no OCR: {e}")
        return ""

def validate_pdf(pdf_bytes: bytes) -> Tuple[bool, str]:
    """
    Valida se o arquivo é um PDF válido
    
    Args:
        pdf_bytes: Conteúdo do arquivo em bytes
    
    Returns:
        Tupla (é_válido, mensagem)
    """
    try:
        if len(pdf_bytes) < 100:
            return False, "Arquivo muito pequeno para ser um PDF"
        
        # Verificar header PDF
        if not pdf_bytes.startswith(b'%PDF-'):
            return False, "Arquivo não possui header PDF válido"
        
        # Tentar abrir com PyMuPDF
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if len(pdf_doc) == 0:
            pdf_doc.close()
            return False, "PDF não contém páginas"
        
        if pdf_doc.needs_pass:
            pdf_doc.close()
            return False, "PDF protegido por senha"
        
        pdf_doc.close()
        return True, "PDF válido"
        
    except Exception as e:
        return False, f"Erro ao validar PDF: {e}"

# Função de teste para desenvolvimento
def test_extraction():
    """Função de teste para verificar se a extração funciona"""
    try:
        # Criar um PDF simples para teste
        import fitz
        
        # Criar documento de teste
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4
        
        # Adicionar texto
        text = "TESTE DE EXTRAÇÃO\nExtractBrowser EC2\nPDF gerado para teste"
        page.insert_text((50, 50), text, fontsize=12)
        
        # Salvar como bytes
        pdf_bytes = doc.tobytes()
        doc.close()
        
        logger.info("🧪 Testando extração com PDF de teste...")
        
        # Testar validação
        is_valid, msg = validate_pdf(pdf_bytes)
        logger.info(f"Validação: {is_valid} - {msg}")
        
        # Testar extração de info
        info = get_pdf_info(pdf_bytes)
        logger.info(f"Info: {info}")
        
        # Testar extração de preview
        preview_bytes = extract_pdf_preview(pdf_bytes)
        if preview_bytes:
            logger.info(f"✅ Preview extraído: {len(preview_bytes)} bytes")
            return True
        else:
            logger.error("❌ Falha na extração de preview")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    # Configurar logging para teste
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    print("🧪 Testando módulo de extração PDF...")
    success = test_extraction()
    print(f"Resultado: {'✅ Sucesso' if success else '❌ Falha'}")
