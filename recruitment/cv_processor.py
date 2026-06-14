import logging
import os
import subprocess
import pdfplumber

logger = logging.getLogger(__name__)

# Tentativa de importar dependências opcionais de OCR
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def _find_tesseract():
    """Localiza o executável do Tesseract em caminhos comuns do Windows."""
    candidatos = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\manue\scoop\apps\tesseract\current\tesseract.exe',
    ]
    for caminho in candidatos:
        if os.path.exists(caminho):
            return caminho
    # Verificar se está no PATH
    try:
        resultado = subprocess.run(
            ['where', 'tesseract'], capture_output=True, text=True, timeout=5
        )
        if resultado.returncode == 0:
            return resultado.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return None


def _poppler_disponivel():
    """Verifica se o poppler está instalado (necessário para pdf2image)."""
    try:
        resultado = subprocess.run(
            ['pdftoppm', '-v'], capture_output=True, text=True, timeout=5
        )
        return resultado.returncode == 0
    except Exception:
        return False


# Configura o Tesseract uma vez no arranque do módulo
if OCR_AVAILABLE:
    caminho_tesseract = _find_tesseract()
    if caminho_tesseract:
        pytesseract.pytesseract.tesseract_cmd = caminho_tesseract


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrai texto de um ficheiro PDF.

    Estratégia:
    1. Tenta pdfplumber (PDFs com texto incorporado).
    2. Se o resultado for insuficiente (< 50 caracteres), usa OCR com
       pytesseract via pdf2image — requer Tesseract e Poppler instalados.

    Retorna uma string UTF-8 limpa.
    """
    texto = ""

    # --- Fase 1: pdfplumber ---
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pagina in pdf.pages:
                conteudo = pagina.extract_text()
                if conteudo:
                    texto += conteudo + "\n"
    except Exception as erro:
        logger.error(f"[cv_processor] pdfplumber falhou: {erro}")

    # --- Fase 2: OCR como fallback ---
    if len(texto.strip()) < 50:
        if not OCR_AVAILABLE:
            logger.warning("[cv_processor] pytesseract/pdf2image não instalados — OCR indisponível.")
            return texto.strip()

        if not _poppler_disponivel():
            logger.warning("[cv_processor] Poppler não encontrado — OCR indisponível.")
            return texto.strip()

        caminho_tesseract = _find_tesseract()
        if not caminho_tesseract:
            logger.warning("[cv_processor] Tesseract não encontrado — OCR indisponível.")
            return texto.strip()

        try:
            imagens = convert_from_path(pdf_path)
            for imagem in imagens:
                texto += pytesseract.image_to_string(imagem, lang="por") + "\n"
        except Exception as erro:
            logger.error(f"[cv_processor] OCR falhou: {erro}")

    return texto.strip()