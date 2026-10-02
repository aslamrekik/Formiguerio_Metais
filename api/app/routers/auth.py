from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from ..config import config
from ..security import criar_token, verificar_senha, hash_senha

router = APIRouter(prefix="/auth", tags=["auth"])

_admin_hash = None

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Faz login e retorna o token JWT."""
    global _admin_hash
    if _admin_hash is None:
        _admin_hash = hash_senha(config.admin_password)
        
    if form_data.username != config.admin_email or not verificar_senha(form_data.password, _admin_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
        
    token = criar_token({"sub": config.admin_email})
    return {"access_token": token, "token_type": "bearer"}
