import os
import tempfile
import subprocess
import sys
import shutil

# Ensure required secrets are present before any app/settings import during test collection.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "dev_jwt_secret_32_chars_minimum__123456")
os.environ.setdefault("SYNC_HMAC_SECRET", "dev_sync_secret_32_chars_minimum__123456")
os.environ.setdefault("STATION_SECRET_ENC_KEY", "dev_station_key_32_chars_minimum__123456")

def _run_alembic_upgrade_head() -> None:
    alembic = shutil.which("alembic")
    if alembic:
        subprocess.check_call([alembic, "upgrade", "head"], env=os.environ.copy())
        return

    # Fallback: some environments may not install the CLI entrypoint.
    try:
        from alembic.config import main as alembic_main  # type: ignore
    except Exception as e:
        raise RuntimeError("Alembic is required to run tests. Install requirements.txt.") from e
    alembic_main(["upgrade", "head"])

def pytest_configure():
    fd, path = tempfile.mkstemp(prefix="assetiq_test_", suffix=".db")
    os.close(fd)
    db_url = f"sqlite+pysqlite:///{path}"

    os.environ["PLANT_DB_URL"] = db_url
    os.environ["HQ_DB_URL"] = db_url

    _run_alembic_upgrade_head()
