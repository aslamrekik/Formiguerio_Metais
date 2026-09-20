"""POST /auth/login (US-03, Arthur)."""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])

# TODO US-03: login com e-mail e senha, devolvendo JWT.
