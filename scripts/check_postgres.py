"""Verifica se kubuka_user consegue ligar-se a kubuka_db, sem depender do binário
`psql` estar no PATH (usa psycopg2 directamente, tal como o Django). Usado pelo
start.ps1 antes de decidir se vale a pena tentar (re)configurar o PostgreSQL.

Uso:
    python scripts/check_postgres.py [password]   # por omissão: kubuka_pass

Saída: "OK" ou "FALHA,<mensagem>"
"""
import sys

try:
    import psycopg2
except ImportError:
    print('FALHA,psycopg2 nao instalado')
    sys.exit(1)

password = sys.argv[1] if len(sys.argv) > 1 else 'kubuka_pass'

try:
    conn = psycopg2.connect(
        host='127.0.0.1', port=5432,
        dbname='kubuka_db', user='kubuka_user', password=password,
        connect_timeout=5,
    )
    conn.close()
    print('OK')
except Exception as exc:
    print(f'FALHA,{exc}'.replace('\n', ' '))
