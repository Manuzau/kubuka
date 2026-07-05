import sqlite3, re

conn = sqlite3.connect(r'C:\Users\manue\.n8n\database.sqlite')
row = conn.execute(
    'SELECT e.id, e.status, e.startedAt, d.data FROM execution_entity e LEFT JOIN execution_data d ON d.executionId=e.id ORDER BY e.startedAt DESC LIMIT 1'
).fetchone()
print('Execucao:', row[0], '| Status:', row[1], '| Hora:', row[2])

raw = row[3].encode('ascii', errors='replace').decode('ascii')

errors = set()
for pat in [r'Error[^\\",]{0,300}', r'not defined[^\\",]{0,100}', r'timeout[^\\",]{0,100}',
            r'ECONNREFUSED[^\\",]{0,100}', r'statusCode[^\\",]{0,50}',
            r'"[345]\d\d"', r'Cannot [^\\",]{0,150}']:
    for m in re.findall(pat, raw, re.IGNORECASE):
        errors.add(m.strip()[:250])

for e in sorted(errors)[:15]:
    print('>>>', e)
