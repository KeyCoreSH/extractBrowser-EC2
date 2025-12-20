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
        "tipo_documento": "CRLV" | "CRV" | "FICHA_CADASTRAL",
        "dados_veiculo": {{
            "placa": "string - Placa do veículo",
            "placa_anterior": "string - Placa anterior se houver",
            "chassi": "string - Chassi",
            "renavam": "string - Código Renavam",
            "marca_modelo": "string - Marca/Modelo/Versão",
            "ano_fabricacao": "integer - Ano Fabricação",
            "ano_modelo": "integer - Ano Modelo",
            "cor": "string - Cor predominante",
            "combustivel": "string - Combustível",
            "categoria": "string - Categoria (Aluguel, Particular)",
            "especie_tipo": "string - Espécie/Tipo (Carga/Semi-reboque, etc)",
            "carroceria": "string - Tipo de carroceria",
            "potencia_cilindrada": "string - Potência/Cilindrada",
            "motor": "string - Número do motor",
            "lotacao": "string - Lotação",
            "peso_bruto_total": "string - Peso Bruto Total (PBT)",
            "cap_max_tracao": "string - Capacidade Máxima Tração (CMT)",
            "numero_eixos": "string - Número de eixos"
        }},
        "situacao": {{
            "exercicio": "string - Exercício (Ano)",
            "data_emissao": "string - Data de emissão",
            "local_emissao": "string - Local de emissão",
            "observacoes": "string - Observações do veículo",
            "mensagem_senatran": "string - Mensagens do Senatran"
        }},
        "proprietario": {{
            "nome": "string - Nome do proprietário",
            "cpf_cnpj": "string - CPF ou CNPJ",
            "local": "string - Local/Cidade",
            "uf": "string - Estado"
        }},
        "seguro_dpvat": {{
             "categoria_tarifaria": "string",
             "data_quitacao": "string",
             "valor_total": "string"
        }}
    }}
    """
