"""Calculo, explicacao, historico, analise final e relatorio.

Rotas previstas no DAS 9.4 (US-09 a US-18):
POST /corridas, POST /corridas/{id}/explicacao, POST /corridas/{id}/confirmar,
PUT /corridas/{id}/analise-final, GET /corridas, GET /corridas/{id},
GET /corridas/{id}/relatorio.pdf, POST /corridas/importar.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/corridas", tags=["corridas"])
