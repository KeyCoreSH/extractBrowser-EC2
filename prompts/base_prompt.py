"""
Prompt base para extração de dados de documentos
"""


def get_base_prompt(text: str, document_type: str) -> str:
    """
    Gera prompt base para extração de dados com JSON perfeito
    
    Args:
        text: Texto extraído do documento
        document_type: Tipo de documento
        
    Returns:
        Prompt formatado com instruções rigorosas para JSON
    """
    
    schema_mapping = {
        "CPF": get_cpf_schema(),
        "CRV": get_crv_schema(), 
        "ANTT": get_antt_schema(),
        "FATURA_ENERGIA": get_fatura_energia_schema(),
        "CNPJ": get_cnpj_schema(),
        "UNKNOWN": get_generic_schema()
    }
    
    schema = schema_mapping.get(document_type, get_generic_schema())
    document_name = get_document_name(document_type)
    
    return f"""Você é um especialista em extração de dados de documentos brasileiros, especializado em {document_name}.

TAREFA: Extrair informações estruturadas do texto de um documento {document_type} em JSON perfeito.

REGRAS CRÍTICAS PARA JSON PERFEITO:
1. Sua resposta deve conter APENAS o objeto JSON válido
2. NÃO inclua NENHUM texto antes ou depois do JSON
3. NÃO use formatação markdown como ```json ou ```
4. O JSON deve ser 100% válido segundo RFC 7159
5. Use aspas duplas para TODAS as chaves e valores string
6. Se não encontrar uma informação, use null (sem aspas)
7. Mantenha a estrutura EXATA do schema fornecido
8. NÃO remova campos - use null se vazio
9. NÃO adicione vírgulas finais nos objetos
10. Escape caracteres especiais corretamente (\", \\, etc.)

SCHEMA OBRIGATÓRIO DO JSON (copie a estrutura exata):
{schema}

TEXTO DO DOCUMENTO:
{text}

IMPORTANTE: Retorne APENAS o JSON com os valores extraídos do texto, mantendo a estrutura EXATA acima:
"""


def get_document_name(document_type: str) -> str:
    """Retorna o nome completo do tipo de documento"""
    names = {
        "CPF": "Cadastro de Pessoa Física",
        "CRV": "Certificado de Registro de Veículo", 
        "ANTT": "Certificado de Condutor ANTT",
        "FATURA_ENERGIA": "Fatura de Energia Elétrica",
        "CNPJ": "Cadastro Nacional de Pessoa Jurídica",
        "UNKNOWN": "documento genérico"
    }
    return names.get(document_type, "documento")


def get_cpf_schema() -> str:
    """Schema para documentos CPF"""
    return """{
  "cpf": null,
  "nome": null,
  "data_nascimento": null,
  "situacao_cadastral": null,
  "data_inscricao": null,
  "endereco": {
    "logradouro": null,
    "numero": null,
    "complemento": null,
    "bairro": null, 
    "cidade": null,
    "estado": null,
    "cep": null
  },
  "documento_origem": null
}"""


def get_crv_schema() -> str:
    """Schema para Certificado de Registro de Veículo"""
    return """{
  "placa": null,
  "chassi": null,
  "renavam": null,
  "marca_modelo": null,
  "ano_fabricacao": null,
  "ano_modelo": null,
  "cor": null,
  "categoria": null,
  "especie": null,
  "combustivel": null,
  "proprietario": {
    "nome": null,
    "cpf_cnpj": null,
    "endereco": null
  },
  "municipio": null,
  "uf": null
}"""


def get_antt_schema() -> str:
    """Schema para documentos ANTT"""
    return """{
  "nome": null,
  "cpf": null,
  "rg": null,
  "data_nascimento": null,
  "categoria": null,
  "numero_certificado": null,
  "data_emissao": null,
  "data_vencimento": null,
  "curso": null,
  "endereco": {
    "logradouro": null,
    "cidade": null,
    "estado": null,
    "cep": null
  },
  "restricoes": null
}"""


def get_fatura_energia_schema() -> str:
    """Schema para Fatura de Energia Elétrica"""
    return """{
  "nome_cliente": null,
  "cpf_cnpj": null,
  "endereco": {
    "logradouro": null,
    "numero": null,
    "complemento": null,
    "bairro": null,
    "cidade": null,
    "estado": null,
    "cep": null
  },
  "numero_cliente": null,
  "numero_instalacao": null,
  "mes_referencia": null,
  "data_vencimento": null,
  "valor_total": null,
  "consumo_kwh": null,
  "distribuidora": null,
  "codigo_barras": null
}"""


def get_cnpj_schema() -> str:
    """Schema para documentos CNPJ"""
    return """{
  "cnpj": null,
  "razao_social": null,
  "nome_fantasia": null,
  "data_abertura": null,
  "situacao_cadastral": null,
  "atividade_principal": null,
  "endereco": {
    "logradouro": null,
    "numero": null,
    "complemento": null,
    "bairro": null,
    "cidade": null,
    "estado": null,
    "cep": null
  },
  "telefone": null,
  "email": null,
  "capital_social": null
}"""


def get_generic_schema() -> str:
    """Schema genérico para documentos desconhecidos"""
    return """{
  "tipo_documento": null,
  "nome": null,
  "cpf_cnpj": null,
  "documento_numero": null,
  "data_emissao": null,
  "endereco": null,
  "dados_principais": {
    "campo1": null,
    "campo2": null,
    "campo3": null
  },
  "informacoes_adicionais": null
}"""
