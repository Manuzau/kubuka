# KUBUKA - Recrutamento e Seleção com IA

KUBUKA é Sistema web que automatiza o processo de triagem e pré-selecção de candidatos
em empresas angolanas, utilizando Inteligência Artificial para analisar
currículos e gerar pontuações de compatibilidade.

## 🚀 Tecnologias

- **Backend:** Django 5.0, Django REST Framework (DRF)
- **Frontend:** Django Templates, Tailwind CSS (via CDN), Flowbite, Alpine.js
- **Extracção de CV:** pdfplumber, pytesseract (OCR), PyPDF2 para extração de texto
- **Automação:** n8n
- **Inteligência Artificial:** Ollama (llama3.2 — modelo local)
- **Business Intelligence:** Power BI
- **Base de dados:** SQLite
- **Configuração:** django-environ para gestão de variáveis de ambiente


## 🛠️ Como executar o projecto

### 1. Clonar o repositório e preparar o ambiente

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto baseado no `.env.example`:

```bash
cp .env.example .env
```

Edite o `.env` e defina sua `SECRET_KEY` e outras configurações.

### 3. Migrar o banco de dados e criar admin

```bash
python manage.py migrate
python manage.py createsuperuser
```

> **Nota:** Ao criar o superuser, ele terá acesso ao Dashboard de Administrador automaticamente.

### 4. Iniciar o servidor

```bash
python manage.py runserver
```

Acesse em: `http://localhost:8000`

## 🧪 Testes

Para rodar a suíte de testes automatizados:

```bash
python manage.py test
```

## 📂 Estrutura do Projeto

- `/recruitment`: App principal com a lógica de candidatos e currículos.
- `/core`: Configurações globais do Django.
- `/media`: Armazenamento de currículos enviados (configurado em settings).
- `recruitment/api_views.py`: Endpoints da API REST.
- `recruitment/views.py`: Views para renderização de templates HTML.

## 🤖 Notas sobre a IA

Atualmente, a lógica de IA está simulada em `recruitment/views.py`. O sistema:
1. Extrai o texto real do PDF usando `PyPDF2`.
2. Gera um score aleatório entre 50 e 95.
3. Fornece um feedback pré-definido.

Para integrar com OpenAI ou outra LLM, basta substituir o bloco de mock na função `upload_resume` em `views.py`.

## 🛡️ Segurança

- Gestão de chaves via `.env`.
- Permissões granulares: Candidatos só vêem seus próprios dados; Admins vêem tudo.
- Proteção CSRF em todos os formulários.
- Senhas hasheadas nativamente pelo Django.


