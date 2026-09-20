"""Composicao resultante de uma mistura de materiais (DAS 12.1).

C_E = soma(m_i * c_i,E * r_i) / soma(m_i * r_i)

TODO US-07 (Ruann, Grokoski).
"""


def composicao_mistura(itens: list, elementos: tuple = ()) -> dict:
    """itens: lista de (Material, massa_kg). Devolve teor em % por elemento."""
    raise NotImplementedError("US-07")
