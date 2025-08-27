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
    
    return f"""Você é um especialista em extração de dados de CNPJ (Cadastro Nacional da Pessoa Jurídica) brasileiros.

TAREFA: Extrair informações estruturadas do texto de um documento de CNPJ em JSON perfeito.

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

INFORMAÇÕES ESPECÍFICAS DO CNPJ:
- CNPJ (formato xx.xxx.xxx/xxxx-xx)
- Razão Social
- Nome fantasia
- Natureza jurídica
- Atividade econômica principal
- Data de abertura
- Situação cadastral
- Data da situação atual
- Endereço da sede completo
- Capital social
- Porte da empresa
- Responsáveis/sócios
- Dados de contato (telefone, email, site)

SCHEMA OBRIGATÓRIO DO JSON (copie a estrutura exata):
{{
  "cnpj": null,
  "razao_social": null,
  "nome_fantasia": null,
  "natureza_juridica": null,
  "atividade_principal": null,
  "data_abertura": null,
  "situacao_cadastral": null,
  "data_situacao": null,
  "endereco": {{
    "logradouro": null,
    "complemento": null,
    "bairro": null,
    "cidade": null,
    "estado": null,
    "cep": null
  }},
  "capital_social": null,
  "porte": null,
  "responsavel_federativo": null,
  "socios": [
    {{
      "nome": null,
      "cpf_cnpj": null,
      "qualificacao": null
    }}
  ],
  "telefone": null,
  "email": null,
  "site": null
}}

TEXTO DO DOCUMENTO CNPJ:
{text}

IMPORTANTE: Retorne APENAS o JSON com os valores extraídos do texto, mantendo a estrutura EXATA acima:
"""
