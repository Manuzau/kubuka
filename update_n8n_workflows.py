"""
Reconstroi os workflows com configuracao correcta do HTTP Request node V3:
  specifyBody: "json" + jsonBody: expressao n8n

specifyBody "string" no V3 = form-urlencoded (ERRADO para JSON)
specifyBody "json"   no V3 = corpo JSON (CORRECTO)
"""
import sqlite3, json

DB_PATH = r'C:\Users\manue\.n8n\database.sqlite'

CV_WORKFLOW_ID       = 'XgXXXZxjLwPAzjGz'
SCORE_WORKFLOW_ID    = 'niPepZ38tAPvIXPr'
CV_ACTIVE_VERSION    = '7a546d6d-c262-48f6-abc0-1b6ad8d09427'
SCORE_ACTIVE_VERSION = '324a9c1a-a105-4817-98e0-66a8d326ef27'

# Code node: prepara os campos individualmente para o HTTP Request node poder aceder via $json
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
    "  'Analisa o seguinte curriculo e responde APENAS com JSON valido com estes campos: ' +\n"
    "  'score (inteiro 0-100), skills (lista de strings), summary (string), experience (string), ' +\n"
    "  'education (string), languages (string), feedback (string).\\n\\nCurriculo:\\n' + cvText;\n"
    "\n"
    "return [{ json: {\n"
    "  resume_id:    body.resume_id,\n"
    "  callback_url: body.callback_url,\n"
    "  ollamaModel:  'llama3.2:1b',\n"
    "  ollamaStream: false,\n"
    "  ollamaFormat: 'json',\n"
    "  ollamaPrompt: prompt,\n"
    "}}];"
)

CV_CODE_PARSE = (
    "const ollamaResp = $input.first().json;\n"
    "const prev = $('Preparar Pedido').first().json;\n"
    "\n"
    "function toStr(val) {\n"
    "  if (val == null) return '';\n"
    "  if (typeof val === 'string') return val.trim();\n"
    "  if (Array.isArray(val)) return val.map(i => (typeof i === 'object' ? JSON.stringify(i) : String(i))).join(', ');\n"
    "  if (typeof val === 'object') return Object.values(val).filter(Boolean).join(' | ') || JSON.stringify(val);\n"
    "  return String(val);\n"
    "}\n"
    "\n"
    "let analysis = {};\n"
    "try {\n"
    "  const raw = String(ollamaResp.response || '{}');\n"
    "  analysis = JSON.parse(raw.replace(/```json\\s*/gi, '').replace(/```\\s*/g, '').trim());\n"
    "} catch (_) {}\n"
    "\n"
    "return [{ json: {\n"
    "  resume_id:    prev.resume_id,\n"
    "  callback_url: prev.callback_url,\n"
    "  score:      Math.min(100, Math.max(0, parseFloat(analysis.score) || 50)),\n"
    "  skills:     Array.isArray(analysis.skills) ? analysis.skills.map(s => (typeof s === 'object' ? JSON.stringify(s) : String(s))).join(', ') : toStr(analysis.skills) || 'Nao identificadas',\n"
    "  summary:    toStr(analysis.summary)    || 'Resumo nao disponivel',\n"
    "  experience: toStr(analysis.experience) || 'Nao especificada',\n"
    "  education:  toStr(analysis.education)  || 'Nao especificada',\n"
    "  languages:  toStr(analysis.languages)  || 'Nao identificados',\n"
    "  feedback:   toStr(analysis.feedback)   || 'Analise concluida.',\n"
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
            "method": "POST",
            "url": "http://127.0.0.1:11434/api/generate",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {model: $json.ollamaModel, stream: $json.ollamaStream, format: $json.ollamaFormat, prompt: $json.ollamaPrompt} }}",
            "options": {}
        },
        "id": "http-ollama-cv", "name": "Chamar Ollama",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "position": [680, 300]
    },
    {
        "parameters": {"jsCode": CV_CODE_PARSE},
        "id": "code-cv-02", "name": "Processar Resposta",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [920, 300]
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
        "position": [1160, 300]
    }
]

CV_CONNECTIONS = {
    "Webhook": {"main": [[{"node": "Preparar Pedido", "type": "main", "index": 0}]]},
    "Preparar Pedido": {"main": [[{"node": "Chamar Ollama", "type": "main", "index": 0}]]},
    "Chamar Ollama": {"main": [[{"node": "Processar Resposta", "type": "main", "index": 0}]]},
    "Processar Resposta": {"main": [[{"node": "Callback Django", "type": "main", "index": 0}]]}
}

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
    "  'Compara o candidato com a vaga. Responde APENAS com JSON valido com dois campos: ' +\n"
    "  'similarity_score (inteiro 0-100) e match_feedback (string).\\n\\n' +\n"
    "  'Candidato - Skills: ' + skills + ' | Resumo: ' + summary + ' | Experiencia: ' + experience + '\\n' +\n"
    "  'Vaga: ' + jobTitle + ' | Requisitos: ' + requirements;\n"
    "\n"
    "return [{ json: {\n"
    "  application_id: body.application_id,\n"
    "  callback_url:   body.callback_url,\n"
    "  ollamaModel:    'llama3.2:1b',\n"
    "  ollamaStream:   false,\n"
    "  ollamaFormat:   'json',\n"
    "  ollamaPrompt:   prompt,\n"
    "}}];"
)

SCORE_CODE_PARSE = (
    "const ollamaResp = $input.first().json;\n"
    "const prev = $('Preparar Pedido Score').first().json;\n"
    "\n"
    "let result = {};\n"
    "try {\n"
    "  const raw = String(ollamaResp.response || '{}');\n"
    "  result = JSON.parse(raw.replace(/```json\\s*/gi, '').replace(/```\\s*/g, '').trim());\n"
    "} catch (_) {}\n"
    "\n"
    "return [{ json: {\n"
    "  application_id: prev.application_id,\n"
    "  callback_url:   prev.callback_url,\n"
    "  similarity_score: Math.min(100, Math.max(0, parseFloat(result.similarity_score) || 0)),\n"
    "  match_feedback:   String(result.match_feedback || 'Analise nao disponivel.').trim(),\n"
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
            "method": "POST",
            "url": "http://127.0.0.1:11434/api/generate",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ {model: $json.ollamaModel, stream: $json.ollamaStream, format: $json.ollamaFormat, prompt: $json.ollamaPrompt} }}",
            "options": {}
        },
        "id": "http-ollama-score", "name": "Chamar Ollama Score",
        "type": "n8n-nodes-base.httpRequest", "typeVersion": 3,
        "position": [680, 300]
    },
    {
        "parameters": {"jsCode": SCORE_CODE_PARSE},
        "id": "code-score-02", "name": "Processar Score",
        "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [920, 300]
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
        "position": [1160, 300]
    }
]

SCORE_CONNECTIONS = {
    "Webhook Score": {"main": [[{"node": "Preparar Pedido Score", "type": "main", "index": 0}]]},
    "Preparar Pedido Score": {"main": [[{"node": "Chamar Ollama Score", "type": "main", "index": 0}]]},
    "Chamar Ollama Score": {"main": [[{"node": "Processar Score", "type": "main", "index": 0}]]},
    "Processar Score": {"main": [[{"node": "Callback Django Score", "type": "main", "index": 0}]]}
}


def update_workflow(conn, wf_id, version_id, nodes, connections, label):
    nj = json.dumps(nodes, ensure_ascii=False)
    cj = json.dumps(connections, ensure_ascii=False)
    conn.execute('UPDATE workflow_entity SET nodes=?, connections=? WHERE id=?', (nj, cj, wf_id))
    conn.execute('UPDATE workflow_history SET nodes=?, connections=? WHERE versionId=?', (nj, cj, version_id))
    print(f'  [{label}] actualizado — {len(nodes)} nos')


def main():
    conn = sqlite3.connect(DB_PATH)
    print('CV Workflow:')
    update_workflow(conn, CV_WORKFLOW_ID, CV_ACTIVE_VERSION, CV_NODES, CV_CONNECTIONS, 'CV')
    print('Score Workflow:')
    update_workflow(conn, SCORE_WORKFLOW_ID, SCORE_ACTIVE_VERSION, SCORE_NODES, SCORE_CONNECTIONS, 'Score')
    conn.commit()
    conn.close()
    print('Feito.')


if __name__ == '__main__':
    main()
