#!/usr/bin/env python3
"""
Script para instalar automaticamente Poppler para OCR
"""

import os
import sys
import subprocess
import zipfile
import urllib.request
from pathlib import Path

POPPLER_RELEASE_URL = "https://github.com/oschwartz10612/poppler-windows/releases/download/v26.1.0/Release-26.1.0.zip"
INSTALL_PATH = Path(r"C:\poppler")
BIN_PATH = INSTALL_PATH / "bin"

def download_file(url, destination):
    """Download a file from URL"""
    print(f"Baixando {url}...")
    try:
        urllib.request.urlretrieve(url, destination)
        print(f"✓ Download concluído: {destination}")
        return True
    except Exception as e:
        print(f"✗ Erro ao baixar: {e}")
        return False

def extract_zip(zip_path, extract_to):
    """Extract ZIP file"""
    print(f"Extraindo {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"✓ Arquivo extraído para: {extract_to}")
        return True
    except Exception as e:
        print(f"✗ Erro ao extrair: {e}")
        return False

def add_to_path():
    """Add Poppler bin to Windows PATH"""
    print(f"Adicionando {BIN_PATH} ao PATH...")
    try:
        # Update current session PATH
        os.environ['PATH'] = str(BIN_PATH) + os.pathsep + os.environ['PATH']
        print(f"✓ PATH atualizado para esta sessão")
        
        # Also add to system PATH if possible (requires admin)
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r'Environment', 0, winreg.KEY_WRITE)
            current_path = winreg.QueryValueEx(key, 'Path')[0]
            new_path = str(BIN_PATH) + os.pathsep + current_path
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            print(f"✓ PATH atualizado no registro do Windows")
        except Exception as e:
            print(f"⚠ Não foi possível atualizar PATH permanente (requer admin): {e}")
    except Exception as e:
        print(f"✗ Erro ao atualizar PATH: {e}")
        return False
    return True

def verify_installation():
    """Verify Poppler is working"""
    print("\nVerificando instalação...")
    try:
        result = subprocess.run(['pdftoppm', '-v'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ Poppler instalado com sucesso!")
            print(result.stdout[:200])
            return True
    except Exception as e:
        print(f"⚠ Poppler não encontrado no PATH: {e}")
        print(f"  Tente adicionar manualmente: {BIN_PATH}")
    return False

def main():
    print("="*60)
    print("Instalador de Dependências OCR (Poppler + Tesseract)")
    print("="*60)
    
    # Create install directory
    INSTALL_PATH.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Diretório de instalação: {INSTALL_PATH}")
    
    # Download Poppler
    zip_file = INSTALL_PATH / "poppler.zip"
    if not download_file(POPPLER_RELEASE_URL, zip_file):
        print("Erro ao baixar Poppler. Verifique sua conexão com a internet.")
        return False
    
    # Extract Poppler
    if not extract_zip(zip_file, INSTALL_PATH):
        print("Erro ao extrair Poppler.")
        return False
    
    # Add to PATH
    if not add_to_path():
        print("Erro ao atualizar PATH.")
        return False
    
    # Verify
    verify_installation()
    
    # Clean up ZIP
    try:
        os.remove(zip_file)
        print(f"\n✓ Arquivo temporário removido")
    except:
        pass
    
    print("\n" + "="*60)
    print("✓ Instalação concluída!")
    print("="*60)
    print("\nDe agora em diante, você pode executar OCR em PDFs digitalizados.")
    print("Exemplo: .venv\\Scripts\\python.exe -m recruitment.test_cv")
    print("\nNota: Se continuar não funcionando, reinicie o VS Code.")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Erro fatal: {e}")
        sys.exit(1)
