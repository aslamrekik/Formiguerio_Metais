"""Materias-primas e ligas (US-04, US-05, US-06 - Arthur).

Rotas previstas no DAS 9.4:
GET/POST /materias-primas, PUT /materias-primas/{id},
POST /materias-primas/importar, GET/POST /ligas, PUT /ligas/{id}.
"""
from fastapi import APIRouter

router = APIRouter(tags=["cadastros"])
