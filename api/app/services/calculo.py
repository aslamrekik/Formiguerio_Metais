"""Camada de aplicacao: converte modelos do banco em tipos do engine e de volta.

Regra do DAS 9.3: router -> service -> repository. O engine nunca toca no banco.

TODO: calcular (US-09), ganho_esperado (US-15), recalibrar (US-17) e
semelhantes (US-13, ate 5 corridas parecidas para o contexto da explicacao).
"""
