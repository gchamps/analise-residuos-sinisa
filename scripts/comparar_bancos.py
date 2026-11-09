"""
Compara o CONTEÚDO de dois bancos SQLite do projeto (tabela a tabela, linha a linha), ignorando o cabeçalho
do arquivo (que guarda a versão do SQLite e muda entre máquinas). Usado na CI para garantir que o banco
regerado a partir das planilhas é igual ao versionado.

Uso:
    python scripts/comparar_bancos.py banco_a.db banco_b.db
Código de saída 0 se iguais, 1 se diferentes.
"""

import sqlite3
import sys
from pathlib import Path

TABELAS = ["indicador", "municipio", "resultado_indicador", "destinacao_municipio", "etl_meta"]


def abrir(caminho):
    return sqlite3.connect(Path(caminho).resolve().as_uri() + "?mode=ro", uri=True)


def diferencas(caminho_a, caminho_b):
    """Lista de descrições das diferenças (vazia se o conteúdo for igual)."""
    problemas = []
    a, b = abrir(caminho_a), abrir(caminho_b)
    try:
        for tabela in TABELAS:
            consulta = f"SELECT * FROM {tabela} ORDER BY 1"      # a 1ª coluna é a chave (ou parte dela) nas 5 tabelas
            try:
                linhas_a, linhas_b = a.execute(consulta).fetchall(), b.execute(consulta).fetchall()
            except sqlite3.OperationalError as erro:
                problemas.append(f"{tabela}: não pôde ser lida em um dos bancos ({erro})")
                continue
            linhas_a, linhas_b = sorted(linhas_a, key=repr), sorted(linhas_b, key=repr)   # ordem total, independe de empates
            if linhas_a != linhas_b:
                n_dif = sum(1 for x, y in zip(linhas_a, linhas_b) if x != y) + abs(len(linhas_a) - len(linhas_b))
                problemas.append(f"{tabela}: {len(linhas_a)} x {len(linhas_b)} linhas, {n_dif} diferentes")
    finally:
        a.close()
        b.close()
    return problemas


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    achados = diferencas(sys.argv[1], sys.argv[2])
    for achado in achados:
        print("DIFERENTE ->", achado)
    if achados:
        sys.exit(1)
    print("Bancos com o mesmo conteúdo.")
