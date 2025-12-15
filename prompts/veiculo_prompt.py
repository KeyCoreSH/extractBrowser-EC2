from typing import Dict, Any

def get_veiculo_prompt(text: str) -> str:
    """
    Gera prompt para estruturação de dados de documentos veiculares (CRV, CRLV, Ficha de Cadastro)
    """
    return f"""
    Analise o texto extraído de um documento veicular (CRV, CRLV ou Ficha Cadastral de Veículo).
    
    TEXTO EXTRAÍDO:
    \"\"\"
    {text}
    \"\"\"
    
    Instruções:
    1. Identifique os dados principais do veículo e do proprietário.
    2. Normalize datas para AAAA-MM-DD.
    3. Extraia informações técnicas detalhadas se disponíveis.
    
    Retorne APENAS um JSON com a seguinte estrutura:
    
    {{
        "dados_veiculo": {{
            "placa": "...",
            "placa_anterior": "...",
            "chassi": "...",
            "renavam": "...",
            "marca_modelo": "...",
            "ano_fabricacao": 0000,
            "ano_modelo": 0000,
            "cor": "...",
            "combustivel": "...",
            "categoria": "...",
            "especie": "...",
            "tipo": "...",
            "potencia": "...",
            "cilindrada": "...",
            "motor": "...",
            "lotacao": "...",
            "peso_bruto_total": "..."
        }},
        "situacao": {{
            "exercicio": "ANO",
            "restricoes": ["alienacao", "restricao_judicial", "roubo_furto", ...],
            "observacoes": "..."
        }},
        "proprietario": {{
            "nome": "...",
            "cpf_cnpj": "...",
            "endereco": "...",
            "cidade": "...",
            "uf": "..."
        }}
    }}
    """
