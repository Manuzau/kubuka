"""Repoe o KUBUKA num estado limpo de raiz: apaga TODOS os dados (base de dados
e CVs em media/resumes/) e recria o schema do zero via `migrate`, ficando so
com um superutilizador. Pensado para validar a solucao com CVs reais/
anonimizados sem ruido de dados de teste.

Protege-se contra execucao acidental em producao: recusa-se a correr se
DEBUG=False ou se a base de dados nao for local.

Uso:
    python manage.py reset_sistema                # pede confirmacao (escrever o nome da BD)
    python manage.py reset_sistema --no-input      # sem prompts
    python manage.py reset_sistema --keep-media    # nao apaga os CVs em media/resumes/
    python manage.py reset_sistema --no-superuser  # nao cria o superutilizador no final

Credenciais do superutilizador (variaveis de ambiente, com omissoes sensatas):
    DJANGO_SUPERUSER_USERNAME  (omissao: admin)
    DJANGO_SUPERUSER_EMAIL     (omissao: admin@kubuka.local)
    DJANGO_SUPERUSER_PASSWORD  (omissao: Kubuka#Demo2026)
"""
import glob
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections

LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}


class Command(BaseCommand):
    help = "Apaga todos os dados de teste e repoe o KUBUKA num estado limpo, com um unico superutilizador."

    def add_arguments(self, parser):
        parser.add_argument("--no-input", action="store_true", help="Nao pedir confirmacao interactiva.")
        parser.add_argument("--keep-media", action="store_true", help="Nao apagar os CVs em media/resumes/.")
        parser.add_argument("--no-superuser", action="store_true", help="Nao criar o superutilizador no final.")

    def handle(self, *args, **options):
        self._check_safety()

        db = settings.DATABASES["default"]
        is_postgres = "postgresql" in db["ENGINE"]
        no_input = options["no_input"]

        if not no_input:
            kind = "PostgreSQL" if is_postgres else "SQLite"
            where = db.get("HOST") or "(ficheiro local)"
            self.stdout.write(self.style.WARNING(
                f"\nISTO VAI APAGAR PERMANENTEMENTE todos os dados de '{db['NAME']}' ({kind} em {where})."
            ))
            confirm = input(f"Escreve o nome da base de dados para confirmar ({db['NAME']}): ")
            if confirm != db["NAME"]:
                raise CommandError("Confirmacao nao corresponde - a abortar sem alterar nada.")

        backup_path = self._backup(db, is_postgres, no_input)

        self.stdout.write("A recriar a base de dados...")
        if is_postgres:
            self._reset_postgres(db)
        else:
            self._reset_sqlite(db)

        connection.close()
        self.stdout.write("A aplicar migracoes...")
        call_command("migrate", interactive=False, verbosity=1)

        media_deleted = 0
        if not options["keep_media"]:
            media_deleted = self._clean_media()

        superuser_info = None
        if not options["no_superuser"]:
            superuser_info = self._create_superuser()

        self._print_summary(backup_path, media_deleted, superuser_info, options)

    # ------------------------------------------------------------------

    def _check_safety(self):
        if not settings.DEBUG:
            raise CommandError("Recusa-se a correr com DEBUG=False - protecao contra execucao em producao.")

        # Nota: core/settings.py cai sozinho para SQLite quando o Postgres configurado
        # (DB_HOST) nao esta acessivel - por isso validamos sempre o DB_HOST pedido no
        # ambiente, mesmo quando o motor activo acabou por ser SQLite, para nao deixar
        # passar um DB_HOST de producao só porque a ligacao falhou silenciosamente.
        requested_host = os.environ.get("DB_HOST", "localhost").lower()
        if requested_host not in LOCAL_HOSTS:
            raise CommandError(
                f"Recusa-se a correr com DB_HOST='{requested_host}' - protecao contra producao."
            )

        db = settings.DATABASES["default"]
        if "sqlite" in db["ENGINE"]:
            return
        host = (db.get("HOST") or "").lower()
        if host not in LOCAL_HOSTS:
            raise CommandError(f"Recusa-se a correr contra um host nao-local ('{host}') - protecao contra producao.")

    def _backup(self, db, is_postgres, no_input):
        backups_dir = Path(settings.BASE_DIR) / "backups"
        backups_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not is_postgres:
            db_file = Path(db["NAME"])
            if not db_file.exists():
                self.stdout.write(self.style.WARNING("Sem ficheiro SQLite existente para copiar - a saltar backup."))
                return None
            dest = backups_dir / f"{db_file.stem}_{timestamp}.sqlite3"
            shutil.copy2(db_file, dest)
            self.stdout.write(self.style.SUCCESS(f"Backup (copia do ficheiro SQLite): {dest}"))
            return dest

        pg_dump = self._find_pg_dump()
        dest = backups_dir / f"{db['NAME']}_{timestamp}.sql"

        if not pg_dump:
            msg = "'pg_dump' nao encontrado - nao consigo criar o backup automatico."
            if no_input:
                raise CommandError(f"{msg} A abortar (usa --no-input só depois de confirmares que aceitas isto).")
            if input(f"{msg} Continuar SEM backup? (escreve 'sim' para continuar): ").strip().lower() != "sim":
                raise CommandError("A abortar - recusa a continuar sem backup sem confirmacao explicita.")
            self.stdout.write(self.style.WARNING("A continuar sem backup, conforme confirmado."))
            return None

        env = os.environ.copy()
        env["PGPASSWORD"] = db["PASSWORD"]
        cmd = [
            pg_dump, "-h", db["HOST"] or "127.0.0.1", "-p", str(db["PORT"] or 5432),
            "-U", db["USER"], "-d", db["NAME"], "-f", str(dest),
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise CommandError(f"pg_dump falhou (exit {result.returncode}): {result.stderr}")
        self.stdout.write(self.style.SUCCESS(f"Backup criado: {dest}"))
        return dest

    def _find_pg_dump(self):
        found = shutil.which("pg_dump")
        if found:
            return found
        candidates = sorted(glob.glob(r"C:\Program Files\PostgreSQL\*\bin\pg_dump.exe"), reverse=True)
        return candidates[0] if candidates else None

    def _reset_postgres(self, db):
        import psycopg2

        admin_conn = psycopg2.connect(
            host=db["HOST"] or "127.0.0.1", port=db["PORT"] or 5432,
            dbname="postgres", user=db["USER"], password=db["PASSWORD"],
            connect_timeout=10,
        )
        admin_conn.autocommit = True
        try:
            with admin_conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid();",
                    (db["NAME"],),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{db["NAME"]}";')
                cur.execute(f'CREATE DATABASE "{db["NAME"]}" OWNER "{db["USER"]}" ENCODING \'UTF8\' TEMPLATE template0;')
        finally:
            admin_conn.close()
        self.stdout.write(self.style.SUCCESS(f"Base de dados '{db['NAME']}' recriada."))

    def _reset_sqlite(self, db):
        db_file = Path(db["NAME"])
        if db_file.exists():
            connections["default"].close()
            db_file.unlink()
        self.stdout.write(self.style.SUCCESS(f"Ficheiro SQLite '{db_file}' apagado."))

    def _clean_media(self):
        media_root = Path(settings.MEDIA_ROOT) / "resumes"
        if not media_root.exists():
            media_root.mkdir(parents=True, exist_ok=True)
            return 0
        count = 0
        for item in media_root.rglob("*"):
            if item.is_file():
                item.unlink()
                count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} ficheiro(s) de CV apagado(s) de media/resumes/."))
        return count

    def _create_superuser(self):
        from django.contrib.auth import get_user_model

        UserModel = get_user_model()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@kubuka.local")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Kubuka#Demo2026")

        user = UserModel.objects.create_superuser(username, email, password)
        user.is_admin = True
        if hasattr(user, "recruiter_approved"):
            user.recruiter_approved = True
        user.save()
        self.stdout.write(self.style.SUCCESS(
            f"Superutilizador '{username}' criado (is_superuser, is_staff, is_admin)."
        ))
        return {"username": username, "email": email, "password": password}

    def _print_summary(self, backup_path, media_deleted, superuser_info, options):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 50))
        self.stdout.write(self.style.MIGRATE_HEADING("  Reset concluido"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 50))
        self.stdout.write(f"  Backup:          {backup_path or '(nenhum)'}")
        if options["keep_media"]:
            self.stdout.write("  CVs:             mantidos (--keep-media)")
        else:
            self.stdout.write(f"  CVs apagados:    {media_deleted}")
        if superuser_info:
            self.stdout.write(f"  Superutilizador: {superuser_info['username']} / {superuser_info['password']}")
        else:
            self.stdout.write("  Superutilizador: nao criado (--no-superuser)")
        self.stdout.write("")
        self.stdout.write("  Contagens actuais:")
        for model in apps.get_app_config("recruitment").get_models():
            self.stdout.write(f"    {model.__name__}: {model.objects.count()}")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 50))
