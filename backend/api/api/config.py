from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ESPOSTI_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://esposti:esposti@localhost:5432/esposti"
    ambiente: str = "sviluppo"  # il seed sintetico gira solo in "sviluppo"
    sessione_durata_ore: int = 8
    cookie_secure: bool = True
    login_max_tentativi: int = 5
    login_finestra_minuti: int = 15
    # archivio documenti (cartella locale, fuori dal repository) e file temporanei del worker
    archivio_radice: str = "~/.esposti/archivio"
    dir_temporanea: str | None = None
    max_mb_per_file: int = 50
    max_file_per_richiesta: int = 20
    # motore: vuoto = finto motore nello stesso processo; altrimenti URL (es. http://motore:8080)
    motore_url: str = ""
    motore_max_tentativi: int = 3
    motore_timeout_secondi: float = 600.0
    motore_intervallo_secondi: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
