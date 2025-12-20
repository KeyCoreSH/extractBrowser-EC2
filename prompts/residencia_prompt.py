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
        "tipo_documento": "CONTA_ENERGIA" | "CONTA_AGUA" | "CONTA_TELECOM" | "CONTA_GAS" | "OUTROS",
        "concessionaria": {{
            "nome": "string - Nome da Concessionária",
            "cnpj": "string - CNPJ da Concessionária"
        }},
        "dados_conta": {{
            "mes_referencia": "string - Mês de referência (MM/AAAA)",
            "vencimento": "string - Data de vencimento (AAAA-MM-DD)",
            "valor_total": "float - Valor total da fatura",
            "numero_instalacao": "string - Número da instalação/inscrição",
            "codigo_cliente": "string - Código do cliente/Matrícula",
            "numero_nota_fiscal": "string - Número da Nota Fiscal",
            "data_emissao": "string - Data de emissão",
            "codigo_barras": "string - Linha digitável ou código de barras"
        }},
        "cliente": {{
            "nome": "string - Nome do titular",
            "cpf_cnpj": "string - CPF ou CNPJ do titular",
             "numero_cliente": "string - Número de identificação do cliente"
        }},
        "endereco_instalacao": {{
            "logradouro": "string - Rua/Av",
            "numero": "string - Número",
            "complemento": "string - Complemento",
            "bairro": "string - Bairro",
            "municipio": "string - Cidade",
            "uf": "string - UF",
            "cep": "string - CEP"
        }},
        "leituras": {{
            "leitura_atual": "string - Data/Valor Leitura Atual",
            "leitura_anterior": "string - Data/Valor Leitura Anterior",
            "proxima_leitura": "string - Previsão próxima leitura",
            "consumo_faturado": "string - Consumo total faturado (kWh, m³)"
        }},
        "historico_consumo": [
            {{
                "mes": "string - Mês/Ano",
                "consumo": "string - Valor consumido"
            }}
        ]
    }}
    """
