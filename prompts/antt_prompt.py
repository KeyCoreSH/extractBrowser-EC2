from typing import Dict, Any

def get_antt_prompt(text: str) -> str:
    """
    Gera prompt para estruturação de dados de documentos ANTT
    """
    return f"""
    Analise o texto extraído de um Extrato ou Certificado ANTT.
    O texto pode estar desformatado devido ao OCR, com linhas de tabelas misturadas.
    
    TEXTO EXTRAÍDO:
    \"\"\"
    {text}
    \"\"\"
    
    Instruções de Extração:
    1. CABEÇALHO: Procure por pares Chave/Valor.
       Ex: "RNTRC:" seguido de números. "RAZÃO SOCIAL:" seguido do nome. "CNPJ:" seguido do número.
    
    2. VEÍCULOS (Parte mais importante):
       O texto dos veículos costuma aparecer em blocos sequenciais ou misturados.
       Procure por padrões de PLACA (AAA-0000 ou AAA0A00) e RENAVAM (aprox 9-11 dígitos).
       Um bloco de veículo geralmente contém: 
       - Placa (ex: MRK-1B41/SC)
       - Renavam (ex: 00930203976)
       - Tipo (Automotor, Implemento)
       - Categoria/Descrição (Caminhão Trator, Semi-Reboque)
       - Situação (Ativo)
       
       Identifique e liste TODOS os veículos encontrados no texto.
    
    3. ENDEREÇO:
       Procure por Logradouro, Bairro, CEP (xxxxx-xxx) e Cidade/UF.
    
    Retorne APENAS um JSON válido. Não inclua markdown ```json`.
    
    Estrutura Exata:
    {{
        "tipo_documento": "CERTIFICADO_ANTT" | "EXTRATO_ANTT",
        "transportador": {{
            "rntrc": "string - RNTRC encontrado",
            "razao_social_nome": "string - Nome ou Razão Social",
            "cpf_cnpj": "string - CPF ou CNPJ (apenas números)",
            "situacao_rntrc": "string - Situação do RNTRC (Ativo/Suspenso)",
            "categoria": "string - Categoria (ETC, TAC, CTC)",
            "data_cadastro": "string - Data de cadastro",
            "data_validade": "string - Data de validade se houver",
            "data_emissao": "string - Data de emissão do documento"
        }},
        "endereco": {{
            "logradouro": "string - Logradouro completo",
            "numero": "string - Número",
            "complemento": "string - Complemento",
            "bairro": "string - Bairro",
            "cidade": "string - Município",
            "uf": "string - UF",
            "cep": "string - CEP"
        }},
        "resumo_frota": {{
            "total_veiculos": "integer - Total de veículos",
            "veiculos_ativos": "integer - Total ativos",
            "veiculos_automotores": "integer - Qtd automotores",
            "veiculos_implementos": "integer - Qtd implementos"
        }},
        "responsavel_tecnico": {{
            "nome": "string",
            "cpf": "string"
        }},
        "veiculos": [
            {{
                "placa": "string - Placa do veículo",
                "renavam": "string - Renavam",
                "tipo": "string - Tipo (Automotor/Implemento)",
                "tipo_carroceria": "string - Descrição/Carroceria",
                "situacao": "string - Situação (Ativo/Outro)",
                "propriedade": "string - Propriedade (Arrendado/Próprio/Leasing)"
            }}
        ]
    }}
    """
