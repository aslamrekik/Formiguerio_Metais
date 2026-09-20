"""Tipos do dominio usados pelo motor (ver DAS secao 7, diagrama de classes).

TODO US-07: definir Material, Faixa, Liga, Banho, Adicao, Desvio e
ResultadoCorrecao como dataclasses, seguindo o diagrama de classes do DAS.
"""

# Elementos controlados no MVP. Al e o restante ate 100%.
# Confirmar a lista final com o engenheiro do cliente.
ELEMENTOS = ("Si", "Fe", "Cu", "Mn", "Mg", "Zn", "Ti", "Ni", "Pb", "Sn")
