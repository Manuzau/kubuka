from recruitment.cv_processor import extract_text_from_pdf

text = extract_text_from_pdf('C:\\Users\\manue\\Desktop\\kubuka\\media\\resumes\\tome_CV.pdf')
print(f"Total de caracteres extraídos: {len(text)}")
print("\n" + "="*60 + "\n")
print(text)