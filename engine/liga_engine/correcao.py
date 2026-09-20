"""Correcao do banho pelo menor custo, por programacao linear (DAS 12.2).

minimizar   soma(p_j * x_j)
sujeito a   L_E * (M0 + soma x_j) <= M0*c0_E + soma(x_j * c_j,E * rho_E)
                                  <= U_E * (M0 + soma x_j)
            0 <= x_j <= estoque_j
            M0 + soma x_j <= capacidade

Regras (DAS 12.4):
- adicao so aumenta a proporcao de um elemento; excesso de Fe ou Cu so se
  corrige diluindo com material pobre nesse elemento;
- sem solucao viavel, devolver status INVIAVEL e o elemento que impede;
- mesma entrada, mesma saida, sempre.

Sugestao: scipy.optimize.linprog com method="highs".

TODO US-09 (Ruann, Grokoski).
"""


def calcular_correcao(banho, liga, materiais, recuperacao: dict = None,
                      versao_calibracao: str = None):
    """Devolve ResultadoCorrecao: adicoes em kg, composicao prevista e desvios."""
    raise NotImplementedError("US-09")
