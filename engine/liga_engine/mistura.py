"""Composicao resultante de uma mistura de materiais (DAS 12.1).

C_E = soma(m_i * c_i,E * r_i) / soma(m_i * r_i)

m_i = massa do material, c_i,E = teor do elemento E no material, r_i = rendimento.
O rendimento pondera a massa: material que rende menos participa menos do banho.

US-07 (Ruann, Grokoski).
"""
from .tipos import ELEMENTOS


def composicao_mistura(itens: list, elementos: tuple = ELEMENTOS) -> dict:
    """Teor em % por elemento de uma mistura de materiais (DAS 12.1).

    itens: lista de (Material, massa_kg).
    elementos: elementos a calcular; por padrao os controlados no MVP.

    Contrato: mistura vazia, massas nulas ou rendimentos nulos (denominador 0)
    devolvem {} - nao ha metal util para falar em composicao. Elemento ausente
    em um material conta como 0. Deterministico: mesma entrada, mesma saida.
    """
    denominador = sum(massa * material.rendimento for material, massa in itens)
    if denominador <= 0:
        return {}

    resultado = {}
    for elemento in elementos:
        numerador = sum(
            massa * material.teor(elemento) * material.rendimento
            for material, massa in itens
        )
        resultado[elemento] = numerador / denominador
    return resultado
