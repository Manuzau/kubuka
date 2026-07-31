"""
Reconstroi os workflows do n8n para o KUBUKA.

Estrutura de 5 nos por workflow:
  Webhook -> Code (preparar) -> HTTP Request (Ollama) -> Code (processar) -> HTTP Request (Django callback)

Modelo: qwen2.5:3b (melhor a produzir JSON estruturado que o llama3.2:1b)
Parsers: busca recursiva pelos campos em qualquer estrutura devolvida pelo LLM

Uso:
    python scripts/update_n8n_workflows.py                  # BD do n8n do utilizador actual
    python scripts/update_n8n_workflows.py --db-path CAMINHO # BD noutro sítio (ex: outra máquina)

Os workflows são identificados pelo NOME (não por um ID fixo) - o ID que o n8n atribui
depende de cada importação/máquina, por isso não pode ser hardcoded. É preciso tê-los
importado pelo menos uma vez (Workflows -> Import from File, ver README) antes de correr
este script - ele só actualiza nós/conexões de workflows já existentes, não os cria.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / '.n8n' / 'database.sqlite'

CV_WORKFLOW_NAME    = 'KUBUKA — Análise de CV'
SCORE_WORKFLOW_NAME = 'KUBUKA — Scoring de Candidatura'

# Dois modelos locais: llama3.2:1b (rapido) para analise de CV, qwen2.5:3b (melhor) para scoring
OLLAMA_MODEL_CV    = 'llama3.2:1b'
OLLAMA_MODEL_SCORE = 'qwen2.5:3b'

# Equivalentes na cloud (Groq, API compativel com OpenAI) - usados apenas se AI_PROVIDER=cloud
# no ambiente do n8n. Ver variavel de ambiente GROQ_API_KEY.
CLOUD_MODEL_CV    = 'llama-3.1-8b-instant'
CLOUD_MODEL_SCORE = 'llama-3.3-70b-versatile'


# ---------- CV Workflow ----------

CV_CODE_PREPARE = (
    "const wh = $input.first().json;\n"
    "const body = (wh.resume_id !== undefined) ? wh : (wh.body || wh);\n"
    "\n"
    "if (!body.resume_id || !body.callback_url) {\n"
    "  throw new Error('Dados em falta: resume_id=' + body.resume_id + ' callback_url=' + body.callback_url);\n"
    "}\n"
    "\n"
    "const cvText = String(body.cv_text || '').slice(0, 6000);\n"
    "const prompt =\n"
    "  'Es um especialista em recrutamento. Analisa o seguinte curriculo e extrai a informacao.\\n\\n' +\n"
    "  'CURRICULO:\\n' + cvText + '\\n\\n' +\n"
    "  'Responde APENAS com um objecto JSON plano contendo:\\n' +\n"
    "  'score: numero inteiro 0-100 (qualidade global do CV).\\n' +\n"
    "  'skills: array de strings com as competencias identificadas.\\n' +\n"
    "  'summary: resumo profissional em portugues.\\n' +\n"
    "  'experience: descricao da experiencia profissional em portugues.\\n' +\n"
    "  'education: formacao academica em portugues.\\n' +\n"
    "  'languages: idiomas em portugues.\\n' +\n"
    "  'feedback: analise em portugues com pontos fortes e sugestoes de melhoria.';\n"
    "\n"
    "return [{ json: {\n"
    "  resume_id:    body.resume_id,\n"
    "  callback_url: body.callback_url,\n"
    "  ollamaModel:  '" + OLLAMA_MODEL_CV + "',\n"
    "  cloudModel:   '" + CLOUD_MODEL_CV + "',\n"
    "  ollamaStream: false,\n"
    "  ollamaFormat: 'json',\n"
    "  ollamaPrompt: prompt,\n"
    "}}];"
)

# Parser CV: busca recursiva por cada campo em qualquer estrutura devolvida pelo LLM
CV_CODE_PARSE = (
    "const ollamaResp = $input.first().json;\n"
    "const prev = $('Preparar Pedido').first().json;\n"
    "\n"
    "function findField(obj, names) {\n"
    "  if (obj == null) return undefined;\n"
    "  if (typeof obj !== 'object') return undefined;\n"
    "  for (const k of Object.keys(obj)) {\n"
    "    if (names.includes(k.toLowerCase())) return obj[k];\n"
    "  }\n"
    "  for (const k of Object.keys(obj)) {\n"
    "    const v = obj[k];\n"
    "    if (v && typeof v === 'object') {\n"
    "      const nested = findField(v, names);\n"
    "      if (nested !== undefined) return nested;\n"
    "    }\n"
    "  }\n"
    "  return undefined;\n"
    "}\n"
    "\n"
    "function toStr(val) {\n"
    "  if (val == null) return '';\n"
    "  if (typeof val === 'string') return val.trim();\n"
    "  if (Array.isArray(val)) return val.map(i => (typeof i === 'object' ? toStr(i) : String(i))).filter(Boolean).join(', ');\n"
    "  if (typeof val === 'object') {\n"
    "    const parts = Object.entries(val).map(([k,v]) => k + ': ' + toStr(v)).filter(x => x.length > 5);\n"
    "    return parts.join(' | ') || JSON.stringify(val);\n"
    "  }\n"
    "  return String(val);\n"
    "}\n"
    "\n"
    "let analysis = {};\n"
    "try {\n"
    "  // 'response' -> formato Ollama; 'choices[0].message.content' -> formato OpenAI-compativel (Groq)\n"
    "  const raw = String(\n"
    "    ollamaResp.response ||\n"
    "    (ollamaResp.choices && ollamaResp.choices[0] && ollamaResp.choices[0].message && ollamaResp.choices[0].message.content) ||\n"
    "    '{}'\n"
    "  );\n"
    "  const cleaned = raw.replace(/```json\\s*/gi, '').replace(/```\\s*/g, '').trim();\n"
    "  analysis = JSON.parse(cleaned);\n"
    "  if (typeof analysis !== 'object' || analysis === null) analysis = {};\n"
    "} catch (_) {}\n"
    "\n"
    "const scoreRaw     = findField(analysis, ['score','cv_score','overall_score','quality_score']);\n"
    "const skillsRaw    = findField(analysis, ['skills','competencias','habilidades']);\n"
    "const summaryRaw   = findField(analysis, ['summary','resumo','sumario']);\n"
    "const experienceRaw= findField(analysis, ['experience','experiencia']);\n"
    "const educationRaw = findField(analysis, ['education','educacao','formacao']);\n"
    "const languagesRaw = findField(analysis, ['languages','idiomas','linguas']);\n"
    "const feedbackRaw  = findField(analysis, ['feedback','analise','comentario']);\n"
    "\n"
    "return [{ json: {\n"
    "  resume_id:    prev.resume_id,\n"
    "  callback_url: prev.callback_url,\n"
    "  score:      Math.min(100, Math.max(0, parseFloat(scoreRaw) || 50)),\n"
    "  skills:     toStr(skillsRaw)     || 'Nao identificadas',\n"
    "  summary:    toStr(summaryRaw)    || 'Resumo nao disponivel',\n"
    "  experience: toStr(experienceRaw) || 'Nao especificada',\n"
    "  education:  toStr(educationRaw)  || 'Nao especificada',\n"
    "  languages:  toStr(languagesRaw)  || 'Nao identificados',\n"
    "  feedback:   toStr(feedbackRaw)   || 'Analise concluida.',\n"
    "}}];"
)

CV_NODES = [
    {
        "parameters": {"httpMethod": "POST", "path": "cv-analysis", "responseMode": "onReceived", "options": {}},
        "id": "wh-cv-01", "name": "Webhook",
        "type": "n8n-nodes-base.webhook", "typeVersion": 1,
        "position": [200, 300],
        "webhookId": "a1b2c3d4-e5f6-7890-abcd-000000000001"
    },
    {
        "parameters": {"jsCode": CV_CODE_PREPARE},
        "id": "code-cv-01", "name": "Preparar Pedido",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [440, 300]
    },
    {
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [
                    {
                        "id": "cond-provider-cv",
                        "leftValue": "={{ $env.AI_PROVIDER }}",
                        "rightValue": "cloud",
                        "operator": {"type": "string", "operation": "equals"}
                    }
                ],
                "combinator": "and"
            },
            "options": {}
        },
        "id": "if-provider-cv", "name": "Escolher Motor de IA",
        "type": "n8n-nodes-base.if", "typeVersion": 2,
        "position": [680, 300]
    },
    {
        "parameters": {
            "method": "POST",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"},
                {"name": "Authorization", "value": "=Bearer {{ $env.GROQ_API_KEY }}"}
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {model: $json.cloudModel, temperature: 0.3, response_format: {type: \"json_object\"}, messages: [ {role: \"user\", content: $json.ollamaPrompt} ]} }}",
            "options": {"timeout": 60000}
        },
        "id": "http-groq-cv", "name": "Chamar Groq",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "onError": "continueErrorOutput",
        "position": [940, 160]
    },
    {
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:11434/api/generate",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {model: $json.ollamaModel, stream: $json.ollamaStream, format: $json.ollamaFormat, prompt: $json.ollamaPrompt} }}",
            "options": {"timeout": 600000}
        },
        "id": "http-ollama-cv", "name": "Chamar Ollama",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "onError": "continueErrorOutput",
        "position": [940, 440]
    },
    {
        # Rede de seguranca inversa: se AI_PROVIDER=cloud e a Groq falhar (ex: quota
        # esgotada), tenta o Ollama local antes de desistir. Nó separado do "Chamar
        # Ollama" de cima para não criar um ciclo Groq<->Ollama no grafo do n8n - este
        # não tem saída de erro própria, se também falhar a execução termina aqui.
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:11434/api/generate",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {model: $json.ollamaModel, stream: $json.ollamaStream, format: $json.ollamaFormat, prompt: $json.ollamaPrompt} }}",
            "options": {"timeout": 600000}
        },
        "id": "http-ollama-cv-fallback", "name": "Chamar Ollama (fallback da Groq)",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "position": [940, 60]
    },
    {
        "parameters": {"jsCode": CV_CODE_PARSE},
        "id": "code-cv-02", "name": "Processar Resposta",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [1180, 300]
    },
    {
        "parameters": {
            "method": "POST",
            "url": "={{ $json.callback_url }}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"},
                {"name": "X-Kubuka-Secret", "value": "kubuka-secret-token-2025"}
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {score: $json.score, skills: $json.skills, summary: $json.summary, experience: $json.experience, education: $json.education, languages: $json.languages, feedback: $json.feedback} }}",
            "options": {}
        },
        "id": "http-django-cv", "name": "Callback Django",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "position": [1420, 300]
    }
]

CV_CONNECTIONS = {
    "Webhook": {"main": [[{"node": "Preparar Pedido", "type": "main", "index": 0}]]},
    "Preparar Pedido": {"main": [[{"node": "Escolher Motor de IA", "type": "main", "index": 0}]]},
    "Escolher Motor de IA": {"main": [
        [{"node": "Chamar Groq", "type": "main", "index": 0}],
        [{"node": "Chamar Ollama", "type": "main", "index": 0}]
    ]},
    "Chamar Groq": {"main": [
        [{"node": "Processar Resposta", "type": "main", "index": 0}],
        [{"node": "Chamar Ollama (fallback da Groq)", "type": "main", "index": 0}]
    ]},
    "Chamar Ollama": {"main": [
        [{"node": "Processar Resposta", "type": "main", "index": 0}],
        [{"node": "Chamar Groq", "type": "main", "index": 0}]
    ]},
    "Chamar Ollama (fallback da Groq)": {"main": [[{"node": "Processar Resposta", "type": "main", "index": 0}]]},
    "Processar Resposta": {"main": [[{"node": "Callback Django", "type": "main", "index": 0}]]}
}


# ---------- Score Workflow ----------

SCORE_CODE_PREPARE = (
    "const wh = $input.first().json;\n"
    "const body = (wh.application_id !== undefined) ? wh : (wh.body || wh);\n"
    "\n"
    "if (!body.application_id || !body.callback_url) {\n"
    "  throw new Error('Dados em falta: application_id=' + body.application_id + ' callback_url=' + body.callback_url);\n"
    "}\n"
    "\n"
    "const skills      = String(body.candidate_skills     || '').slice(0, 2000);\n"
    "const summary     = String(body.candidate_summary    || '').slice(0, 1000);\n"
    "const experience  = String(body.candidate_experience || '').slice(0, 2000);\n"
    "const jobTitle    = String(body.job_title            || '');\n"
    "const requirements = String(body.job_requirements   || '').slice(0, 3000);\n"
    "\n"
    "const prompt =\n"
    "  'Es um especialista em recrutamento. Analisa a correspondencia entre o candidato e a vaga abaixo.\\n\\n' +\n"
    "  'CANDIDATO:\\n' +\n"
    "  '- Competencias: ' + skills + '\\n' +\n"
    "  '- Resumo: ' + summary + '\\n' +\n"
    "  '- Experiencia: ' + experience + '\\n\\n' +\n"
    "  'VAGA:\\n' +\n"
    "  '- Titulo: ' + jobTitle + '\\n' +\n"
    "  '- Requisitos: ' + requirements + '\\n\\n' +\n"
    "  'Responde APENAS com um objecto JSON plano com dois campos:\\n' +\n"
    "  'similarity_score: um numero inteiro entre 0 e 100 representando a percentagem de correspondencia.\\n' +\n"
    "  'match_feedback: uma frase em portugues com os pontos fortes e as lacunas do candidato em relacao aos requisitos.';\n"
    "\n"
    "return [{ json: {\n"
    "  application_id: body.application_id,\n"
    "  callback_url:   body.callback_url,\n"
    "  ollamaModel:    '" + OLLAMA_MODEL_SCORE + "',\n"
    "  cloudModel:     '" + CLOUD_MODEL_SCORE + "',\n"
    "  ollamaStream:   false,\n"
    "  ollamaFormat:   'json',\n"
    "  ollamaPrompt:   prompt,\n"
    "}}];"
)

# Parser Score: bulletproof — aceita qualquer estrutura devolvida pelo modelo
SCORE_CODE_PARSE = (
    "const ollamaResp = $input.first().json;\n"
    "const prev = $('Preparar Pedido Score').first().json;\n"
    "\n"
    "function findNumeric(obj, names) {\n"
    "  if (obj == null) return undefined;\n"
    "  if (typeof obj === 'number') return obj;\n"
    "  if (typeof obj === 'string') { const n = parseFloat(obj); return isNaN(n) ? undefined : n; }\n"
    "  if (typeof obj !== 'object') return undefined;\n"
    "  for (const k of Object.keys(obj)) {\n"
    "    if (names.includes(k.toLowerCase())) {\n"
    "      const v = obj[k];\n"
    "      if (typeof v === 'number') return v;\n"
    "      if (typeof v === 'string') { const n = parseFloat(v); if (!isNaN(n)) return n; }\n"
    "    }\n"
    "  }\n"
    "  for (const k of Object.keys(obj)) {\n"
    "    const v = obj[k];\n"
    "    if (v && typeof v === 'object') {\n"
    "      const nested = findNumeric(v, names);\n"
    "      if (nested !== undefined) return nested;\n"
    "    }\n"
    "  }\n"
    "  return undefined;\n"
    "}\n"
    "\n"
    "function findText(obj, names) {\n"
    "  if (obj == null) return undefined;\n"
    "  if (typeof obj !== 'object') return undefined;\n"
    "  for (const k of Object.keys(obj)) {\n"
    "    if (names.includes(k.toLowerCase())) {\n"
    "      const v = obj[k];\n"
    "      if (typeof v === 'string' && v.trim().length > 0) return v.trim();\n"
    "      if (typeof v === 'object' && v !== null) {\n"
    "        const parts = [];\n"
    "        for (const kk of Object.keys(v)) {\n"
    "          const vv = v[kk];\n"
    "          if (typeof vv === 'string') parts.push(vv);\n"
    "        }\n"
    "        if (parts.length) return parts.join(' ');\n"
    "      }\n"
    "    }\n"
    "  }\n"
    "  for (const k of Object.keys(obj)) {\n"
    "    const v = obj[k];\n"
    "    if (v && typeof v === 'object') {\n"
    "      const nested = findText(v, names);\n"
    "      if (nested !== undefined) return nested;\n"
    "    }\n"
    "  }\n"
    "  return undefined;\n"
    "}\n"
    "\n"
    "let parsed = {};\n"
    "try {\n"
    "  // 'response' -> formato Ollama; 'choices[0].message.content' -> formato OpenAI-compativel (Groq)\n"
    "  const raw = String(\n"
    "    ollamaResp.response ||\n"
    "    (ollamaResp.choices && ollamaResp.choices[0] && ollamaResp.choices[0].message && ollamaResp.choices[0].message.content) ||\n"
    "    '{}'\n"
    "  );\n"
    "  const cleaned = raw.replace(/```json\\s*/gi, '').replace(/```\\s*/g, '').trim();\n"
    "  parsed = JSON.parse(cleaned);\n"
    "  if (typeof parsed === 'number') parsed = { similarity_score: parsed };\n"
    "  if (typeof parsed !== 'object' || parsed === null) parsed = {};\n"
    "} catch (_) {}\n"
    "\n"
    "const scoreRaw    = findNumeric(parsed, ['similarity_score','score','match_score','similarity','percentage','match_percentage']);\n"
    "const feedbackRaw = findText(parsed,    ['match_feedback','feedback','explanation','analysis','comentario','analise','justification']);\n"
    "\n"
    "return [{ json: {\n"
    "  application_id: prev.application_id,\n"
    "  callback_url:   prev.callback_url,\n"
    "  similarity_score: Math.min(100, Math.max(0, parseFloat(scoreRaw) || 0)),\n"
    "  match_feedback:   (feedbackRaw || 'Analise concluida.').toString().slice(0, 4000),\n"
    "}}];"
)

SCORE_NODES = [
    {
        "parameters": {"httpMethod": "POST", "path": "job-scoring", "responseMode": "onReceived", "options": {}},
        "id": "wh-score-01", "name": "Webhook Score",
        "type": "n8n-nodes-base.webhook", "typeVersion": 1,
        "position": [200, 300],
        "webhookId": "a1b2c3d4-e5f6-7890-abcd-000000000002"
    },
    {
        "parameters": {"jsCode": SCORE_CODE_PREPARE},
        "id": "code-score-01", "name": "Preparar Pedido Score",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [440, 300]
    },
    {
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [
                    {
                        "id": "cond-provider-score",
                        "leftValue": "={{ $env.AI_PROVIDER }}",
                        "rightValue": "cloud",
                        "operator": {"type": "string", "operation": "equals"}
                    }
                ],
                "combinator": "and"
            },
            "options": {}
        },
        "id": "if-provider-score", "name": "Escolher Motor de IA",
        "type": "n8n-nodes-base.if", "typeVersion": 2,
        "position": [680, 300]
    },
    {
        "parameters": {
            "method": "POST",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"},
                {"name": "Authorization", "value": "=Bearer {{ $env.GROQ_API_KEY }}"}
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {model: $json.cloudModel, temperature: 0.3, response_format: {type: \"json_object\"}, messages: [ {role: \"user\", content: $json.ollamaPrompt} ]} }}",
            "options": {"timeout": 60000}
        },
        "id": "http-groq-score", "name": "Chamar Groq Score",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "onError": "continueErrorOutput",
        "position": [940, 160]
    },
    {
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:11434/api/generate",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {model: $json.ollamaModel, stream: $json.ollamaStream, format: $json.ollamaFormat, prompt: $json.ollamaPrompt} }}",
            "options": {"timeout": 600000}
        },
        "id": "http-ollama-score", "name": "Chamar Ollama Score",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "onError": "continueErrorOutput",
        "position": [940, 440]
    },
    {
        # Rede de seguranca inversa (ver comentario equivalente no workflow de CV).
        "parameters": {
            "method": "POST",
            "url": "http://127.0.0.1:11434/api/generate",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {model: $json.ollamaModel, stream: $json.ollamaStream, format: $json.ollamaFormat, prompt: $json.ollamaPrompt} }}",
            "options": {"timeout": 600000}
        },
        "id": "http-ollama-score-fallback", "name": "Chamar Ollama Score (fallback da Groq)",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "position": [940, 60]
    },
    {
        "parameters": {"jsCode": SCORE_CODE_PARSE},
        "id": "code-score-02", "name": "Processar Score",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [1180, 300]
    },
    {
        "parameters": {
            "method": "POST",
            "url": "={{ $json.callback_url }}",
            "sendHeaders": True,
            "headerParameters": {"parameters": [
                {"name": "Content-Type", "value": "application/json"},
                {"name": "X-Kubuka-Secret", "value": "kubuka-secret-token-2025"}
            ]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {similarity_score: $json.similarity_score, match_feedback: $json.match_feedback} }}",
            "options": {}
        },
        "id": "http-django-score", "name": "Callback Django Score",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "position": [1420, 300]
    }
]

SCORE_CONNECTIONS = {
    "Webhook Score": {"main": [[{"node": "Preparar Pedido Score", "type": "main", "index": 0}]]},
    "Preparar Pedido Score": {"main": [[{"node": "Escolher Motor de IA", "type": "main", "index": 0}]]},
    "Escolher Motor de IA": {"main": [
        [{"node": "Chamar Groq Score", "type": "main", "index": 0}],
        [{"node": "Chamar Ollama Score", "type": "main", "index": 0}]
    ]},
    "Chamar Groq Score": {"main": [
        [{"node": "Processar Score", "type": "main", "index": 0}],
        [{"node": "Chamar Ollama Score (fallback da Groq)", "type": "main", "index": 0}]
    ]},
    "Chamar Ollama Score": {"main": [
        [{"node": "Processar Score", "type": "main", "index": 0}],
        [{"node": "Chamar Groq Score", "type": "main", "index": 0}]
    ]},
    "Chamar Ollama Score (fallback da Groq)": {"main": [[{"node": "Processar Score", "type": "main", "index": 0}]]},
    "Processar Score": {"main": [[{"node": "Callback Django Score", "type": "main", "index": 0}]]}
}


def update_workflow(conn, name, nodes, connections, label):
    """Actualiza nodes/connections do workflow com este nome. Devolve True se encontrou
    e actualizou, False se o workflow ainda não existe (precisa de ser importado primeiro)."""
    cur = conn.execute('SELECT id, activeVersionId FROM workflow_entity WHERE name=?', (name,))
    row = cur.fetchone()
    if row is None:
        print(f'  [{label}] AVISO: workflow "{name}" não encontrado na BD do n8n.')
        print(f'           Importa-o primeiro: n8n -> Workflows -> Import from File.')
        return False

    wf_id, active_version_id = row
    nj = json.dumps(nodes, ensure_ascii=False)
    cj = json.dumps(connections, ensure_ascii=False)

    entity_updated = conn.execute(
        "UPDATE workflow_entity SET nodes=?, connections=?, updatedAt=STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW') WHERE id=?",
        (nj, cj, wf_id),
    ).rowcount

    history_updated = 0
    if active_version_id:
        history_updated = conn.execute(
            "UPDATE workflow_history SET nodes=?, connections=?, updatedAt=STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW') WHERE versionId=?",
            (nj, cj, active_version_id),
        ).rowcount

    if entity_updated == 0:
        print(f'  [{label}] ERRO: UPDATE não afectou nenhuma linha (id={wf_id}).')
        return False

    if history_updated == 0:
        print(f'  [{label}] actualizado ({len(nodes)} nós) - aviso: sem versionId activo, histórico não sincronizado.')
    else:
        print(f'  [{label}] actualizado - {len(nodes)} nós')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('Uso:')[0].strip())
    parser.add_argument('--db-path', default=str(DEFAULT_DB_PATH),
                         help=f'Caminho para a database.sqlite do n8n (por omissão: {DEFAULT_DB_PATH})')
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f'ERRO: base de dados do n8n não encontrada em: {db_path}')
        print('       Confirma que já correste o n8n pelo menos uma vez (n8n start).')
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    print('CV Workflow:')
    ok_cv = update_workflow(conn, CV_WORKFLOW_NAME, CV_NODES, CV_CONNECTIONS, 'CV')
    print('Score Workflow:')
    ok_score = update_workflow(conn, SCORE_WORKFLOW_NAME, SCORE_NODES, SCORE_CONNECTIONS, 'Score')
    conn.commit()
    conn.close()

    if ok_cv and ok_score:
        print('Feito.')
    else:
        print('Concluído com avisos - ver mensagens acima.')
        sys.exit(1)


if __name__ == '__main__':
    main()
