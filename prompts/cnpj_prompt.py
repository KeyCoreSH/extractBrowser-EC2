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
7. Mantenha a estrutura exata do schema fornecido

INFORMAÇÕES ESPECÍFICAS DO CNPJ:
- CNPJ (formato xx.xxx.xxx/xxxx-xx)
- Razão Social
- Nome fantasia
- Natureza jurídica
- Atividade econômica principal
- Data de abertura
- Situação cadastral
- Endereço da sede
- Capital social
- Porte da empresa
- Responsáveis/sócios

SCHEMA DO JSON DE RESPOSTA:
{{
  "cnpj": "string - CNPJ formatado (xx.xxx.xxx/xxxx-xx)",
  "razao_social": "string - Razão social da empresa",
  "nome_fantasia": "string - Nome fantasia",
  "natureza_juridica": "string - Natureza jurídica",
  "atividade_principal": "string - Atividade econômica principal",
  "data_abertura": "string - Data de abertura DD/MM/AAAA",
  "situacao_cadastral": "string - Situação (Ativa, Baixada, etc)",
  "data_situacao": "string - Data da situação atual",
  "endereco": {{
    "logradouro": "string - Logradouro com número",
    "complemento": "string - Complemento",
    "bairro": "string - Bairro",
    "cidade": "string - Município",
    "estado": "string - Estado (sigla)",
    "cep": "string - CEP"
  }},
  "capital_social": "string - Capital social",
  "porte": "string - Porte da empresa",
  "responsavel_federativo": "string - Ente federativo responsável",
  "socios": [
    {{
      "nome": "string - Nome do sócio",
      "cpf_cnpj": "string - CPF ou CNPJ do sócio",
      "qualificacao": "string - Qualificação do sócio"
    }}
  ],
  "telefone": "string - Telefone se presente",
  "email": "string - Email se presente",
  "site": "string - Website se presente"
}}

TEXTO DO DOCUMENTO CNPJ:
{text}

Retorne apenas o JSON estruturado:
"""
