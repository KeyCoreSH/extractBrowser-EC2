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
    
    return f"""Você é um especialista em extração de dados de Carteira Nacional de Habilitação (CNH) brasileira.

TAREFA: Extrair informações estruturadas do texto de uma CNH em JSON perfeito.

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

INFORMAÇÕES ESPECÍFICAS DA CNH:
- Nome completo do portador
- CPF (formato xxx.xxx.xxx-xx)
- RG/Documento de identidade
- Data de nascimento (DD/MM/AAAA)
- Data de primeira habilitação (DD/MM/AAAA)
- Data de emissão desta via (DD/MM/AAAA)
- Data de validade (DD/MM/AAAA)
- Categoria habilitada (A, B, C, D, E, AB, AC, AD, AE, etc.)
- Número do registro/CNH
- Local de emissão (cidade/estado)
- Filiação (pai e mãe)
- Endereço completo
- Observações/restrições médicas
- Nacionalidade
- Órgão emissor

SCHEMA OBRIGATÓRIO DO JSON (copie a estrutura exata):
{{
  "nome": null,
  "cpf": null,
  "rg": null,
  "data_nascimento": null,
  "data_primeira_habilitacao": null,
  "data_emissao": null,
  "data_vencimento": null,
  "categoria": null,
  "numero_registro": null,
  "local_emissao": null,
  "endereco": {{
    "logradouro": null,
    "bairro": null,
    "cidade": null,
    "estado": null,
    "cep": null
  }},
  "filiacao": {{
    "pai": null,
    "mae": null
  }},
  "orgao_emissor": null,
  "observacoes": null,
  "nacionalidade": null
}}

TEXTO DA CNH:
{text}

IMPORTANTE: Retorne APENAS o JSON com os valores extraídos do texto, mantendo a estrutura EXATA acima:
"""
