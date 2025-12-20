
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from prompts.antt_prompt import get_antt_prompt
    from prompts.cnh_prompt import get_cnh_prompt
    from prompts.cnpj_prompt import get_cnpj_prompt
    from prompts.residencia_prompt import get_residencia_prompt
    from prompts.veiculo_prompt import get_veiculo_prompt
    
    print("--- TESTING PROMPTS ---")
    
    print("1. ANTT Prompt:")
    try:
        p = get_antt_prompt("TEST ANTT")
        print("   OK - Generated successfully")
    except Exception as e:
        print(f"   FAIL - {e}")
        
    print("2. CNH Prompt:")
    try:
        p = get_cnh_prompt("TEST CNH")
        print("   OK - Generated successfully")
    except Exception as e:
        print(f"   FAIL - {e}")

    print("3. CNPJ Prompt:")
    try:
        p = get_cnpj_prompt("TEST CNPJ")
        print("   OK - Generated successfully")
    except Exception as e:
        print(f"   FAIL - {e}")

    print("4. Residencia Prompt:")
    try:
        p = get_residencia_prompt("TEST RESIDENCIA")
        print("   OK - Generated successfully")
    except Exception as e:
        print(f"   FAIL - {e}")

    print("5. Veiculo Prompt:")
    try:
        p = get_veiculo_prompt("TEST VEICULO")
        print("   OK - Generated successfully")
    except Exception as e:
        print(f"   FAIL - {e}")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    sys.exit(1)
