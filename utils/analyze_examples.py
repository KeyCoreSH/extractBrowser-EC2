
import os
import fitz
import sys

EXAMPLES_DIR = "/Users/rogerioalencarfilho/Projetos/clientes/asfora/doc-ocr/extractBrowser-EC2/documents-examples"

def analyze_pdf(path):
    print(f"\n--- ANALYZING: {os.path.basename(path)} ---")
    try:
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        print(text[:2000] + ("..." if len(text) > 2000 else "")) # Limit output
        return text
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return ""

if __name__ == "__main__":
    if not os.path.exists(EXAMPLES_DIR):
        print(f"Directory not found: {EXAMPLES_DIR}")
        sys.exit(1)
        
    files = sorted([f for f in os.listdir(EXAMPLES_DIR) if f.lower().endswith('.pdf')])
    
    for f in files:
        path = os.path.join(EXAMPLES_DIR, f)
        analyze_pdf(path)
