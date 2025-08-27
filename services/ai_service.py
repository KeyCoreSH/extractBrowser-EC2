"""
Serviço de IA para estruturação de dados de documentos
"""
import json
import logging
import os
import requests
from typing import Dict, Any, Optional

from prompts.base_prompt import get_base_prompt
from prompts.cnh_prompt import get_cnh_prompt

logger = logging.getLogger(__name__)

# Configurações da IA
AI_MAX_TOKENS = 1500
AI_TEMPERATURE = 0.1
AI_TIMEOUT = 30


class AIService:
    """
    Serviço de IA para estruturação de dados usando OpenAI API
    """
    
    def __init__(self):
        """Inicializa o serviço de IA"""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_url = "https://api.openai.com/v1/chat/completions"
        
        # Log da configuração (sem expor a chave completa)
        if self.openai_api_key:
            key_preview = f"{self.openai_api_key[:10]}...{self.openai_api_key[-4:]}" if len(self.openai_api_key) > 14 else "****"
            logger.info(f"OPENAI_API_KEY configurada: {key_preview}")
            self.openai_available = True
        else:
            logger.warning("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
            self.openai_available = False
    
    def structure_data(self, text: str, document_type: str) -> Dict[str, Any]:
        """
        Estrutura dados extraídos usando IA
        
        Args:
            text: Texto extraído do documento
            document_type: Tipo do documento (CNH, ANTT, CNPJ, etc.)
            
        Returns:
            Dicionário com dados estruturados e metadados
        """
        try:
            logger.info(f"Iniciando estruturação de dados para tipo: {document_type}")
            
            # Obter prompt específico para o tipo de documento
            prompt = self._get_prompt_for_document_type(text, document_type)
            
            if not prompt:
                logger.error(f"Tipo de documento não suportado: {document_type}")
                return {
                    "success": False,
                    "error": f"Tipo de documento '{document_type}' não é suportado",
                    "data": {},
                    "confidence": 0.0,
                    "metadata": {
                        "document_type": document_type,
                        "ai_provider": "openai",
                        "processing_time": 0
                    }
                }
            
            # Estruturar dados com OpenAI (se disponível)
            if self.openai_available:
                structured_data = self._structure_with_openai(prompt)
                
                if structured_data:
                    logger.info("Dados estruturados com sucesso")
                    return {
                        "success": True,
                        "data": structured_data,
                        "confidence": 0.8,
                        "metadata": {
                            "document_type": document_type,
                            "ai_provider": "openai",
                            "model": "gpt-4o-mini",
                            "extracted_fields": len(structured_data) if isinstance(structured_data, dict) else 0
                        }
                    }
            
            # Fallback para resposta estruturada básica sem IA
            logger.warning("OpenAI não disponível - retornando estrutura básica")
            return {
                "success": False,
                "error": "Serviço de IA não disponível",
                "data": {},
                "confidence": 0.0,
                "metadata": {
                    "document_type": document_type,
                    "ai_provider": "none",
                    "processing_time": 0
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na estruturação de dados: {str(e)}")
            return {
                "success": False,
                "error": f"Erro interno: {str(e)}",
                "data": {},
                "confidence": 0.0,
                "metadata": {
                    "document_type": document_type,
                    "ai_provider": "error",
                    "processing_time": 0
                }
            }
    
    def _get_prompt_for_document_type(self, text: str, document_type: str) -> Optional[str]:
        """
        Obtém o prompt específico para o tipo de documento
        
        Args:
            text: Texto extraído
            document_type: Tipo do documento
            
        Returns:
            Prompt formatado ou None se tipo não suportado
        """
        try:
            document_type = document_type.upper()
            
            if document_type == "CNH":
                return get_cnh_prompt(text)
            elif document_type in ["ANTT", "CPF", "CRV", "FATURA_ENERGIA", "CNPJ"]:
                return get_base_prompt(text, document_type)
            else:
                logger.warning(f"Tipo de documento não reconhecido: {document_type}")
                # Usar prompt genérico
                return get_base_prompt(text, "UNKNOWN")
                
        except Exception as e:
            logger.error(f"Erro ao obter prompt: {str(e)}")
            return None
    
    def _structure_with_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Estrutura dados usando API OpenAI
        
        Args:
            prompt: Prompt formatado para o modelo
            
        Returns:
            Dados estruturados ou None se falhar
        """
        try:
            logger.info("Estruturando dados com OpenAI GPT-4o-mini")
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um especialista em extração de dados de documentos brasileiros. "
                                 "Analise o texto fornecido e extraia as informações solicitadas em formato JSON válido."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": AI_MAX_TOKENS,
                "temperature": AI_TEMPERATURE
            }
            
            # Fazer requisição para API OpenAI
            response = requests.post(
                self.openai_url,
                json=payload,
                headers=headers,
                timeout=AI_TIMEOUT
            )
            
            # Verificar se a requisição foi bem-sucedida
            if response.status_code != 200:
                logger.error(f"Erro na API OpenAI: {response.status_code} - {response.text}")
                return None
            
            # Parse da resposta
            response_data = response.json()
            
            if not response_data.get('choices'):
                logger.error("Resposta vazia da API OpenAI")
                return None
            
            content = response_data['choices'][0]['message']['content']
            
            if not content:
                logger.error("Conteúdo vazio na resposta da API OpenAI")
                return None
            
            # Limpar e fazer parse do JSON
            cleaned_content = self._clean_json_response(content)
            structured_data = json.loads(cleaned_content)
            
            logger.info("Dados estruturados com sucesso usando API OpenAI")
            return structured_data
            
        except requests.exceptions.Timeout:
            logger.error("Timeout na requisição para API OpenAI")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para API OpenAI: {str(e)}")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON da API OpenAI: {str(e)}")
            logger.error(f"Conteúdo recebido: {content[:500]}...")
            return None
            
        except Exception as e:
            logger.error(f"Erro na API OpenAI: {str(e)}")
            return None
    
    def _clean_json_response(self, content: str) -> str:
        """
        Limpa a resposta para extrair apenas o JSON válido
        
        Args:
            content: Conteúdo bruto da resposta
            
        Returns:
            JSON limpo como string
        """
        try:
            # Remover markdown e texto extra
            content = content.strip()
            
            # Procurar por blocos JSON
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()
            
            # Procurar pelo primeiro { e último }
            start = content.find("{")
            end = content.rfind("}") + 1
            
            if start != -1 and end > start:
                content = content[start:end]
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao limpar JSON: {str(e)}")
            return content
    
    def validate_structured_data(self, data: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """
        Valida dados estruturados baseado no tipo de documento
        
        Args:
            data: Dados estruturados
            document_type: Tipo do documento
            
        Returns:
            Resultado da validação com score de confiança
        """
        try:
            logger.info(f"Validando dados estruturados para tipo: {document_type}")
            
            validation_result = {
                "is_valid": True,
                "confidence": 0.8,
                "errors": [],
                "warnings": []
            }
            
            if not isinstance(data, dict):
                validation_result["is_valid"] = False
                validation_result["confidence"] = 0.0
                validation_result["errors"].append("Dados não estão em formato de dicionário")
                return validation_result
            
            # Validações específicas por tipo de documento
            if document_type.upper() == "CNH":
                validation_result = self._validate_cnh_data(data, validation_result)
            elif document_type.upper() == "CNPJ":
                validation_result = self._validate_cnpj_data(data, validation_result)
            elif document_type.upper() == "CPF":
                validation_result = self._validate_cpf_data(data, validation_result)
            
            logger.info(f"Validação concluída. Válido: {validation_result['is_valid']}, "
                       f"Confiança: {validation_result['confidence']}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Erro na validação: {str(e)}")
            return {
                "is_valid": False,
                "confidence": 0.0,
                "errors": [f"Erro na validação: {str(e)}"],
                "warnings": []
            }
    
    def _validate_cnh_data(self, data: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Valida dados específicos de CNH"""
        required_fields = ["nome", "cpf", "categoria"]
        
        for field in required_fields:
            if not data.get(field):
                validation_result["errors"].append(f"Campo obrigatório ausente: {field}")
                validation_result["is_valid"] = False
        
        # Validar CPF (formato básico)
        cpf = data.get("cpf", "")
        if cpf and len(cpf.replace(".", "").replace("-", "")) != 11:
            validation_result["warnings"].append("CPF pode estar em formato incorreto")
            validation_result["confidence"] *= 0.9
        
        return validation_result
    
    def _validate_cnpj_data(self, data: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Valida dados específicos de CNPJ"""
        required_fields = ["razao_social", "cnpj"]
        
        for field in required_fields:
            if not data.get(field):
                validation_result["errors"].append(f"Campo obrigatório ausente: {field}")
                validation_result["is_valid"] = False
        
        # Validar CNPJ (formato básico)
        cnpj = data.get("cnpj", "")
        if cnpj and len(cnpj.replace(".", "").replace("/", "").replace("-", "")) != 14:
            validation_result["warnings"].append("CNPJ pode estar em formato incorreto")
            validation_result["confidence"] *= 0.9
        
        return validation_result
    
    def _validate_cpf_data(self, data: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Valida dados específicos de CPF"""
        required_fields = ["nome", "cpf"]
        
        for field in required_fields:
            if not data.get(field):
                validation_result["errors"].append(f"Campo obrigatório ausente: {field}")
                validation_result["is_valid"] = False
        
        return validation_result
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Verifica status de saúde do serviço
        
        Returns:
            Status de saúde do serviço
        """
        return {
            "ai_service": "ready",
            "openai_available": self.openai_available,
            "models": {
                "openai": "gpt-4o-mini"
            }
        }
