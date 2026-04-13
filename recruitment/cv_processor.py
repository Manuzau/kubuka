import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import os
import subprocess
import sys

def find_tesseract():
    """Find Tesseract executable in common locations"""
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\manue\scoop\apps\tesseract\current\tesseract.exe',
        r'C:\tesseract\tesseract.exe',
        'tesseract.exe'  # In PATH
    ]
    
    for path in possible_paths:
        if os.path.exists(path) or (path == 'tesseract.exe' and is_tesseract_in_path()):
            return path
    return None

def is_tesseract_in_path():
    """Check if tesseract is in PATH"""
    try:
        result = subprocess.run(['where', 'tesseract'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False

def is_poppler_installed():
    """Check if poppler is installed and available"""
    try:
        result = subprocess.run(['pdftoppm', '-v'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False

def extract_text_from_pdf(pdf_path):
    text = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        print(f"[ERROR] Erro ao extrair com pdfplumber: {str(e)}")

    if len(text.strip()) < 50:
        if not is_poppler_installed():
            print(POPPLER_INSTRUCTIONS)
            return text.strip() if text.strip() else ""
        
        if not tesseract_path:
            print("⚠️  Tesseract não encontrado. Instale primeiro:")
            print("   choco install tesseract -y")
            return text.strip() if text.strip() else ""
        
        try:
            images = convert_from_path(pdf_path)
            for image in images:
                text += pytesseract.image_to_string(image, lang="por") + "\n"
        except Exception as e:
            print(f"[ERROR] Erro ao extrair com OCR: {str(e)}")

    return text.strip()