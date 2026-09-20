"""Variaveis de ambiente (DAS 10.3). Valores reais so no painel do Render."""
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    database_url: str = "postgresql+psycopg://liga:liga@localhost:5432/liga"
    jwt_secret: str = "troque-em-producao"
    jwt_horas: int = 8
    admin_email: str = "admin@liga.app"
    admin_password: str = "trocar-no-primeiro-acesso"
    cors_origin: str = "http://localhost:5173"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_model_reserva: str = "gemini-3.5-flash-lite"
    gemini_timeout_s: float = 15.0

    class Config:
        env_file = ".env"


config = Config()
