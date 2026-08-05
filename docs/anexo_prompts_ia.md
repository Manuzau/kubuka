# Anexo — Prompts de IA utilizados no n8n

Fonte canónica: `scripts/update_n8n_workflows.py` (script que escreve estes nós directamente
nos workflows do n8n — `KUBUKA — Análise de CV` e `KUBUKA — Scoring de Candidatura`).

Ambos os prompts são enviados ao motor de IA (Ollama local ou Groq na cloud, consoante a
variável de ambiente `AI_PROVIDER`) dentro de um nó *Code* ("Preparar Pedido"), com os
espaços reservados (`{{ ... }}`) substituídos pelos dados reais da candidatura no momento do
pedido.

| | Modelo local (Ollama) | Modelo cloud (Groq) |
|---|---|---|
| Análise de CV | `llama3.2:1b` | `llama-3.1-8b-instant` |
| Scoring de Candidatura | `qwen2.5:3b` | `llama-3.3-70b-versatile` |

---

## 1. Prompt — Análise de CV

Usado quando o candidato submete o currículo (`webhook/cv-analysis`), para preencher os
campos `score`, `skills`, `summary`, `experience`, `education`, `languages` e `feedback` do
modelo `Resume`.

```
És um especialista em recrutamento em Angola. Analisa o currículo abaixo e devolve APENAS
um objecto JSON válido, sem texto antes ou depois, seguindo exactamente esta estrutura:

{
  "score": 72,
  "skills": ["Gestão de projectos", "Excel avançado", "Comunicação"],
  "summary": "Resumo profissional em português.",
  "experience": "Descrição da experiência profissional em português.",
  "education": "Formação académica em português.",
  "languages": "Idiomas identificados.",
  "feedback": "Análise em português com pontos fortes e sugestões de melhoria."
}

Critérios para o campo score (número inteiro de 0 a 100):
- Clareza e estrutura do CV (secções bem definidas, informação fácil de localizar).
- Relevância e profundidade da experiência profissional descrita.
- Presença de resultados concretos ou quantificáveis (ex: aumentou vendas em 20%).
- Adequação da formação e competências ao perfil descrito.
Um currículo vazio, incompleto ou ilegível deve ter score abaixo de 30, e o feedback deve
explicar essa limitação em vez de inventar informação que não existe no texto.

O campo skills deve ter entre 5 e 15 competências técnicas e comportamentais reais
mencionadas ou claramente implícitas no currículo, sem repetições.

Responde sempre em português, mesmo que o currículo esteja noutra língua.

CURRÍCULO:
{{cv_text}}
```

*(`{{cv_text}}` — texto do currículo extraído por `cv_processor.py`, truncado a 6000
caracteres antes de ser enviado ao modelo.)*

---

## 2. Prompt — Scoring de Candidatura (correspondência candidato × vaga)

Usado quando o candidato se candidata a uma vaga (`webhook/job-scoring`), para preencher
`similarity_score` e `match_feedback` do modelo `Application`.

```
És um especialista em recrutamento em Angola. Analisa a correspondência entre o candidato
e a vaga abaixo.

CANDIDATO:
- Competências: {{candidate_skills}}
- Resumo: {{candidate_summary}}
- Experiência: {{candidate_experience}}

VAGA:
- Título: {{job_title}}
- Requisitos: {{job_requirements}}

Devolve APENAS um objecto JSON válido, sem texto antes ou depois, seguindo exactamente esta
estrutura:

{
  "similarity_score": 68,
  "match_feedback": "Duas a três frases em português com os pontos fortes e depois as
  lacunas do candidato face aos requisitos."
}

Critérios para o campo similarity_score (número inteiro de 0 a 100):
- Competências técnicas do candidato que correspondem aos requisitos da vaga (peso 40%).
- Relevância e nível da experiência profissional face ao que a vaga exige (peso 35%).
- Adequação da formação académica, quando mencionada (peso 15%).
- Idiomas, quando relevantes para a vaga (peso 10%).
Se faltar informação do candidato para avaliar algum critério, considera esse critério
neutro em vez de penalizar ou beneficiar sem base.

Responde sempre em português, mesmo que os dados estejam noutra língua.
```

*(`{{candidate_skills}}`, `{{candidate_summary}}`, `{{candidate_experience}}`,
`{{job_title}}`, `{{job_requirements}}` — dados da candidatura e da vaga, truncados a 2000,
1000, 2000 e 3000 caracteres respectivamente antes de serem enviados ao modelo.)*

---

## Nota metodológica

- Ambos os prompts exigem resposta em **JSON estrito** (sem texto antes/depois), para que o
  nó seguinte do workflow (`Processar Resposta` / `Processar Score`) consiga extrair os
  campos de forma automática e robusta — o parser procura os campos recursivamente em
  qualquer estrutura devolvida pelo modelo, tolerando pequenas variações de formatação.
- Os critérios de pontuação (pesos, limiares) estão explicitados directamente no prompt para
  reduzir a subjectividade e a variabilidade das respostas do modelo entre execuções.
- Em caso de falta de informação do candidato, o prompt de scoring instrui o modelo a tratar
  esse critério como neutro, evitando penalizações injustas por ausência de dados (e não por
  fraca adequação real).
