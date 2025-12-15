from typing import Dict, Any

def get_residencia_prompt(text: str) -> str:
    """
    Gera prompt para estruturação de dados de Comprovantes de Residência (Conta de Luz, Água, Telefone, Internet, etc.)
    """
    return f"""
    Analise o texto extraído de um comprovante de residência (Conta de consumo: Energia, Água, Gás, Internet, etc.).
    
    TEXTO EXTRAÍDO:
    \"\"\"
    {text}
    \"\"\"
    
    Instruções:
    1. Identifique a concessionária/empresa emissora.
    2. Identifique o titular e o endereço COMPLETO.
    3. Normalize datas para AAAA-MM-DD e valores numéricos (float, separado por ponto).
    
    Retorne APENAS um JSON com a seguinte estrutura:
    
    {{
        "tipo_conta": "ENERGIA" | "AGUA" | "TELECOM" | "GAS" | "OUTROS",
        "emissor": {{
            "nome_empresa": "Nome da Concessionária",
            "cnpj": "CNPJ da Concessionária"
        }},
        "fatura": {{
            "mes_referencia": "MM/AAAA",
            "vencimento": "AAAA-MM-DD",
            "valor_total": 0.00,
            "numero_instalacao": "...",
            "codigo_cliente": "...",
            "codigo_barras": "..."
        }},
        "titular": {{
            "nome": "...",
            "cpf_cnpj": "..."
        }},
        "endereco_instalacao": {{
            "logradouro": "Rua/Av...",
            "numero": "...",
            "complemento": "...",
            "bairro": "...",
            "cidade": "...",
            "uf": "..."
        }},
        "leituras": {{
            "leitura_atual": "...",
            "leitura_anterior": "...",
            "consumo": "..."
        }}
    }}
    """
