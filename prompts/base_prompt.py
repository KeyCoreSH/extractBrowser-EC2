"""
Prompt base para extração de dados de documentos
"""


def get_base_prompt(text: str, document_type: str) -> str:
    """
    Gera prompt base para extração de dados
    
    Args:
        text: Texto extraído do documento
        document_type: Tipo de documento
        
    Returns:
        Prompt formatado
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
    
    return f"""
Você é um especialista em extração de dados de documentos brasileiros.

TAREFA: Extrair informações estruturadas do texto de um documento {document_type}.

REGRAS CRÍTICAS:
1. Sua resposta deve conter APENAS o objeto JSON válido
2. NÃO inclua NENHUM texto antes ou depois do JSON
3. NÃO use formatação markdown como ```json
4. O JSON deve ser 100% válido, sem vírgulas finais
5. Use aspas duplas para todas as chaves e valores string
6. Se não encontrar uma informação, use null para o campo
7. Mantenha a estrutura exata do schema fornecido

SCHEMA DO JSON DE RESPOSTA:
{schema}

TEXTO DO DOCUMENTO:
{text}

Retorne apenas o JSON estruturado:
"""


def get_cpf_schema() -> str:
    """Schema para documentos CPF"""
    return """{
  "cpf": "string - CPF formatado (xxx.xxx.xxx-xx)",
  "nome": "string - Nome completo",
  "data_nascimento": "string - Data no formato DD/MM/AAAA",
  "situacao_cadastral": "string - Situação no CPF",
  "data_inscricao": "string - Data de inscrição",
  "endereco": {
    "logradouro": "string",
    "numero": "string",
    "complemento": "string",
    "bairro": "string", 
    "cidade": "string",
    "estado": "string",
    "cep": "string"
  },
  "documento_origem": "string - Tipo do documento base"
}"""


def get_crv_schema() -> str:
    """Schema para Certificado de Registro de Veículo"""
    return """{
  "placa": "string - Placa do veículo",
  "chassi": "string - Número do chassi",
  "renavam": "string - Número RENAVAM",
  "marca_modelo": "string - Marca e modelo do veículo",
  "ano_fabricacao": "string - Ano de fabricação",
  "ano_modelo": "string - Ano do modelo",
  "cor": "string - Cor do veículo",
  "categoria": "string - Categoria do veículo",
  "especie": "string - Espécie do veículo",
  "combustivel": "string - Tipo de combustível",
  "proprietario": {
    "nome": "string - Nome do proprietário",
    "cpf_cnpj": "string - CPF ou CNPJ",
    "endereco": "string - Endereço completo"
  },
  "municipio": "string - Município de registro",
  "uf": "string - Estado"
}"""


def get_antt_schema() -> str:
    """Schema para documentos ANTT"""
    return """{
  "nome": "string - Nome do condutor",
  "cpf": "string - CPF formatado",
  "rg": "string - Número do RG",
  "data_nascimento": "string - Data no formato DD/MM/AAAA",
  "categoria": "string - Categoria habilitada",
  "numero_certificado": "string - Número do certificado ANTT",
  "data_emissao": "string - Data de emissão",
  "data_vencimento": "string - Data de vencimento",
  "curso": "string - Curso realizado",
  "endereco": {
    "logradouro": "string",
    "cidade": "string",
    "estado": "string",
    "cep": "string"
  },
  "restricoes": "string - Restrições se houver"
}"""


def get_fatura_energia_schema() -> str:
    """Schema para Fatura de Energia Elétrica"""
    return """{
  "nome_cliente": "string - Nome do cliente",
  "cpf_cnpj": "string - CPF ou CNPJ do cliente",
  "endereco": {
    "logradouro": "string - Endereço de instalação",
    "numero": "string",
    "complemento": "string",
    "bairro": "string",
    "cidade": "string",
    "estado": "string",
    "cep": "string"
  },
  "numero_cliente": "string - Número do cliente",
  "numero_instalacao": "string - Número da instalação",
  "mes_referencia": "string - Mês/ano de referência",
  "data_vencimento": "string - Data de vencimento",
  "valor_total": "string - Valor total da fatura",
  "consumo_kwh": "string - Consumo em kWh",
  "distribuidora": "string - Nome da distribuidora",
  "codigo_barras": "string - Código de barras se presente"
}"""


def get_cnpj_schema() -> str:
    """Schema para documentos CNPJ"""
    return """{
  "cnpj": "string - CNPJ formatado (xx.xxx.xxx/xxxx-xx)",
  "razao_social": "string - Razão social",
  "nome_fantasia": "string - Nome fantasia",
  "data_abertura": "string - Data de abertura",
  "situacao_cadastral": "string - Situação cadastral",
  "atividade_principal": "string - Atividade principal",
  "endereco": {
    "logradouro": "string",
    "numero": "string",
    "complemento": "string",
    "bairro": "string",
    "cidade": "string",
    "estado": "string",
    "cep": "string"
  },
  "telefone": "string - Telefone",
  "email": "string - Email",
  "capital_social": "string - Capital social"
}"""


def get_generic_schema() -> str:
    """Schema genérico para documentos desconhecidos"""
    return """{
  "tipo_documento": "string - Tipo detectado do documento",
  "nome": "string - Nome da pessoa se identificado",
  "cpf_cnpj": "string - CPF ou CNPJ se presente",
  "documento_numero": "string - Número do documento",
  "data_emissao": "string - Data de emissão se presente",
  "endereco": "string - Endereço se presente",
  "dados_principais": {
    "campo1": "valor1",
    "campo2": "valor2"
  },
  "informacoes_adicionais": "string - Outras informações relevantes"
}"""
