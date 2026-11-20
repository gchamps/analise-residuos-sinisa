"""Regera, na ordem certa, tudo o que compõe o artigo: evidências do banco, imagens, números, capturas do painel,
HTML e PDF. Pré-requisitos: PostgreSQL portátil ligado (porta 5433), painel no ar (porta 8501), Edge instalado.

Uso, na raiz do projeto: python docs/entrega_abd/gerar_tudo.py <pasta_de_trabalho> <saida.pdf>
"""
import pathlib
import subprocess
import sys

AQUI = pathlib.Path(__file__).resolve().parent
W = pathlib.Path(sys.argv[1]).resolve()
PDF = pathlib.Path(sys.argv[2]).resolve()
W.mkdir(parents=True, exist_ok=True)


def rodar(*args):
    print(">", " ".join(str(a) for a in args))
    subprocess.run([str(a) for a in args], check=True)


rodar(sys.executable, AQUI / "gerar_evidencias.py", W / "ev")
rodar(sys.executable, AQUI / "renderizar_prints.py", W / "ev", W / "png")
rodar(sys.executable, AQUI / "coletar_numeros.py", W / "numeros.json")
rodar(sys.executable, AQUI / "capturar_painel.py", W)
rodar(sys.executable, AQUI / "montar_artigo.py", W, W / "artigo.html")
rodar(sys.executable, AQUI / "imprimir_pdf.py", W / "artigo.html", PDF)
print("PDF:", PDF)
