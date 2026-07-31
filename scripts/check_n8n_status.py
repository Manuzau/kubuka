"""Verificação read-only (não escreve nada) do estado do n8n para o start.ps1 saber se
precisa de mostrar instruções de primeira utilização (criar conta / importar workflows).

Uso:
    python scripts/check_n8n_status.py [caminho-para-database.sqlite]

Saída (uma linha, para o PowerShell fazer parsing fácil):
    <utilizadores>,<workflows-kubuka>
    erro,<mensagem>          # BD inacessível/bloqueada (ex: n8n a escrever nela agora)
"""
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / '.n8n' / 'database.sqlite'


def main():
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    if not db_path.exists():
        print(f'erro,base de dados nao encontrada em {db_path}')
        return

    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=5)
        users = conn.execute('SELECT count(*) FROM "user"').fetchone()[0]
        workflows = conn.execute(
            "SELECT count(*) FROM workflow_entity WHERE name LIKE 'KUBUKA%'"
        ).fetchone()[0]
        conn.close()
        print(f'{users},{workflows}')
    except Exception as exc:
        print(f'erro,{exc}')


if __name__ == '__main__':
    main()
