from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    ad_account_id: str
    access_token: str
    api_version: str
    confirmation_secret: str
    gateway_api_key: str

    @classmethod
    def from_env(cls) -> "Settings":
        values = {
            "ad_account_id": os.getenv("META_AD_ACCOUNT_ID", "").removeprefix("act_"),
            "access_token": os.getenv("META_ACCESS_TOKEN", ""),
            "api_version": os.getenv("META_API_VERSION", ""),
            "confirmation_secret": os.getenv("APP_CONFIRMATION_SECRET", ""),
            "gateway_api_key": os.getenv("GATEWAY_API_KEY", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RuntimeError(f"Variáveis obrigatórias ausentes: {', '.join(missing)}")
        if not values["api_version"].startswith("v"):
            raise RuntimeError("META_API_VERSION deve ter o formato vXX.X")
        if len(values["confirmation_secret"]) < 32:
            raise RuntimeError("APP_CONFIRMATION_SECRET deve ter ao menos 32 caracteres")
        if len(values["gateway_api_key"]) < 32:
            raise RuntimeError("GATEWAY_API_KEY deve ter ao menos 32 caracteres")
        return cls(**values)
