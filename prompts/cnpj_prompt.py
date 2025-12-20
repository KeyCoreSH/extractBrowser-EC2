"""
Prompt específico para extração de dados de CNPJ
"""


def get_cnpj_prompt(text: str) -> str:
    """
    Gera prompt específico para CNPJ com JSON perfeito
    
    Args:
        text: Texto extraído do documento CNPJ
        
    Returns:
        Prompt formatado para CNPJ com instruções rigorosas para JSON
    """
    
    return f"""
Você é um especialista em extração de dados de documentos de CNPJ (Cadastro Nacional da Pessoa Jurídica) brasileiros.

TAREFA: Extrair informações estruturadas do texto de um documento de CNPJ.

REGRAS CRÍTICAS:
1. Sua resposta deve conter APENAS o objeto JSON válido
2. NÃO inclua NENHUM texto antes ou depois do JSON
3. NÃO use formatação markdown como ```json
4. O JSON deve ser 100% válido, sem vírgulas finais
5. Use aspas duplas para todas as chaves e valores string
6. Se não encontrar uma informação, use null para o campo
7. Mantenha a estrutura exata do schema fornecido.
8. TODOS os campos do schema DEVEM estar presentes no JSON, use null se não encontrar o valor.

INFORMAÇÕES ESPECÍFICAS DO CNPJ:
- CNPJ (formato xx.xxx.xxx/xxxx-xx)
- Razão Social e Nome Fantasia
- Datas (Abertura, Situação)
- Endereço e Contato
- Sócios e Capital Social

SCHEMA DO JSON DE RESPOSTA:
{{
  "cnpj": "string - CNPJ formatado",
  "razao_social": "string - Razão Social",
  "nome_fantasia": "string - Nome Fantasia",
  "data_abertura": "string - Data de abertura",
  "situacao_cadastral": "string - Situação (Ativa, etc)",
  "data_situacao_cadastral": "string - Data da situação",
  "natureza_juridica": "string - Código e descrição da natureza jurídica",
  "atividades_economicas": [
    {{
      "codigo": "string - Código CNAE",
      "descricao": "string - Descrição da atividade"
    }}
  ],
  "endereco": {{
    "logradouro": "string - Logradouro",
    "numero": "string - Número",
    "complemento": "string - Complemento",
    "bairro": "string - Bairro",
    "municipio": "string - Município",
    "uf": "string - Estado (sigla)",
    "cep": "string - CEP"
  }},
  "contato": {{
    "telefone_1": "string - Telefone principal",
    "telefone_2": "string - Telefone secundário",
    "email": "string - Email",
    "celular": "string - Celular"
  }},
  "capital_social": "string - Capital social",
  "porte": "string - Porte da empresa",
  "ente_federativo_responsavel": "string - Ente federativo se houver",
  "socios": [
    {{
      "nome": "string - Nome do sócio",
      "cpf_cnpj": "string - CPF ou CNPJ do sócio",
      "qualificacao": "string - Qualificação do sócio"
    }}
  ]
}}

TEXTO DO DOCUMENTO CNPJ:
{text}

Retorne apenas o JSON estruturado:
"""
