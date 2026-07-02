from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


# Load the project-local file before settings are constructed. Existing shell
# variables retain priority, which is useful in deployments and tests.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    db_path: Path
    base_url: str | None
    client_id: str | None
    client_secret: str | None
    timeout_seconds: float


def get_settings() -> Settings:
    return Settings(
        db_path=Path(os.getenv("APPFOLIO_DB_PATH", "./data/appfolio.db")),
        base_url=os.getenv("APPFOLIO_BASE_URL", "").rstrip("/") or None,
        client_id=os.getenv("APPFOLIO_CLIENT_ID") or None,
        client_secret=os.getenv("APPFOLIO_CLIENT_SECRET") or None,
        timeout_seconds=float(os.getenv("APPFOLIO_TIMEOUT_SECONDS", "30")),
    )
