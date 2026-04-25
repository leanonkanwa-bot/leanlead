from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"
    whisper_model: str = "base"

    storage_uploads: str = "storage/uploads"
    storage_outputs: str = "storage/outputs"
    storage_work: str = "storage/work"

    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def uploads_dir(self) -> Path:
        return (BACKEND_DIR / self.storage_uploads).resolve()

    @property
    def outputs_dir(self) -> Path:
        return (BACKEND_DIR / self.storage_outputs).resolve()

    @property
    def work_dir(self) -> Path:
        return (BACKEND_DIR / self.storage_work).resolve()


settings = Settings()

for d in (settings.uploads_dir, settings.outputs_dir, settings.work_dir):
    d.mkdir(parents=True, exist_ok=True)
