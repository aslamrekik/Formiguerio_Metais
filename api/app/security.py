from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from .config import config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')

def hash_senha(senha: str) -> str:
    """Cria um hash bcrypt para a senha."""
    return pwd_context.hash(senha)

def verificar_senha(senha: str, hash: str) -> bool:
    """Verifica se a senha bate com o hash."""
    return pwd_context.verify(senha, hash)

def criar_token(dados: dict) -> str:
    """Cria um token JWT."""
    to_encode = dados.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=config.jwt_horas)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.jwt_secret, algorithm="HS256")

def usuario_atual(token: str = Depends(oauth2_scheme)) -> str:
    """Extrai e valida o usuario do token JWT."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.jwt_secret, algorithms=["HS256"])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return email
