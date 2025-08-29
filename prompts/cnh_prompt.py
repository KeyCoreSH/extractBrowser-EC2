"""
Prompt específico para extração de dados de CNH
"""


def get_cnh_prompt(text: str) -> str:
    """
    Gera prompt específico para CNH com JSON perfeito
    
    Args:
        text: Texto extraído da CNH
        
    Returns:
        Prompt formatado para CNH com instruções rigorosas para JSON
    """
    
    return f"""
Você é um especialista em extração de dados de Carteira Nacional de Habilitação (CNH) brasileira.

TAREFA: Extrair informações estruturadas do texto de uma CNH.

REGRAS CRÍTICAS:
1. Sua resposta deve conter APENAS o objeto JSON válido
2. NÃO inclua NENHUM texto antes ou depois do JSON
3. NÃO use formatação markdown como ```json
4. O JSON deve ser 100% válido, sem vírgulas finais
5. Use aspas duplas para todas as chaves e valores string
6. Se não encontrar uma informação, use null para o campo
7. Mantenha a estrutura exata do schema fornecido

INFORMAÇÕES ESPECÍFICAS DA CNH:
- Nome completo do portador
- CPF (formato xxx.xxx.xxx-xx)
- RG (número de registro)
- Data de nascimento (DD/MM/AAAA)
- Data de emissão (DD/MM/AAAA)
- Data de validade (DD/MM/AAAA)
- Categoria habilitada (A, B, C, D, E, AB, AC, AD, AE)
- Número do registro
- Local de emissão
- Filiação (pai/mãe)
- Endereço completo
- Observações/restrições

SCHEMA DO JSON DE RESPOSTA:
{{
  "nome": "string - Nome completo do portador",
  "cpf": "string - CPF formatado (xxx.xxx.xxx-xx)",
  "rg": "string - Número do RG/Registro",
  "data_nascimento": "string - Data no formato DD/MM/AAAA",
  "data_emissao": "string - Data de emissão DD/MM/AAAA",
  "data_vencimento": "string - Data de validade DD/MM/AAAA",
  "categoria": "string - Categoria(s) habilitada(s)",
  "numero_registro": "string - Número do registro/CNH",
  "local_emissao": "string - Local onde foi emitida",
  "endereco": {{
    "logradouro": "string - Rua/Avenida com número",
    "bairro": "string - Bairro",
    "cidade": "string - Cidade",
    "estado": "string - Estado (sigla)",
    "cep": "string - CEP"
  }},
  "filiacao": {{
    "pai": "string - Nome do pai",
    "mae": "string - Nome da mãe"
  }},
  "orgao_emissor": "string - Órgão emissor (ex: DETRAN)",
  "observacoes": "string - Observações ou restrições se houver",
  "nacionalidade": "string - Nacionalidade do portador",
  "primeira_habilitacao": "string - Data da primeira habilitação"
}}

TEXTO DA CNH:
{text}

Retorne apenas o JSON estruturado:
"""
