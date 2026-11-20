"""Imprime o HTML do artigo em PDF A4 com o cabeçalho padrão da FATEC (logos do Centro Paula Souza e do Governo do Estado,
linha fina e nome da unidade) e numeração de página, usando o Edge em modo headless via protocolo DevTools.

Uso: python docs/entrega_abd/imprimir_pdf.py <artigo.html> <saida.pdf>
O arquivo logo_cps_sp.png (mesmo cabeçalho do artigo de Estatística) fica nesta pasta.
"""
import asyncio
import base64
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
AQUI = pathlib.Path(__file__).resolve().parent
PORTA = 9335
# margens A4 em cm: topo, direita, base, esquerda (o topo abriga o cabeçalho)
TOPO, DIREITA, BASE, ESQUERDA = 3.2, 3.0, 2.2, 3.0
ESCALA_CAB = 1.0     # o Chromium reduz o texto do cabeçalho; ajustável após conferir o PDF


def cabecalho():
    logo = base64.b64encode((AQUI / "logo_cps_sp.png").read_bytes()).decode()
    s = ESCALA_CAB
    return (f'<div style="width:100%;text-align:center;font-family:Arial,sans-serif;-webkit-print-color-adjust:exact">'
            f'<img src="data:image/png;base64,{logo}" style="height:{37*s:.0f}px">'
            f'<div style="margin:{5*s:.0f}px {ESQUERDA}cm 0 {ESQUERDA}cm;border-top:{max(1, round(1*s))}px solid #444;'
            f'padding-top:{6*s:.0f}px;font-size:{15*s:.0f}px;font-weight:bold">'
            f'Fatec São Bernardo do Campo - Adib Moisés Dib</div></div>')


def rodape():
    return ('<div style="width:100%;text-align:center;font-family:Arial,sans-serif;font-size:11px;color:#555">'
            '<span class="pageNumber"></span></div>')


def imprimir(html_path, pdf_path):
    perfil = pathlib.Path(pdf_path).resolve().parent / "_perfil_pdf"
    proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", f"--remote-debugging-port={PORTA}",
                             f"--user-data-dir={perfil}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        abas = None
        for _ in range(60):
            try:
                abas = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/json"))
                break
            except Exception:
                time.sleep(0.3)
        url = [t for t in abas if t["type"] == "page"][0]["webSocketDebuggerUrl"]

        async def principal():
            async with websockets.connect(url, max_size=256 * 1024 * 1024) as ws:
                contador = 0

                async def chamar(metodo, **p):
                    nonlocal contador
                    contador += 1
                    mid = contador
                    await ws.send(json.dumps({"id": mid, "method": metodo, "params": p}))
                    while True:
                        r = json.loads(await ws.recv())
                        if r.get("id") == mid:
                            return r

                await chamar("Page.enable")
                await chamar("Page.navigate", url=pathlib.Path(html_path).resolve().as_uri())
                await asyncio.sleep(3)
                r = await chamar("Page.printToPDF", paperWidth=8.2677, paperHeight=11.6929,
                                 marginTop=TOPO / 2.54, marginBottom=BASE / 2.54,
                                 marginRight=DIREITA / 2.54, marginLeft=ESQUERDA / 2.54,
                                 displayHeaderFooter=True, headerTemplate=cabecalho(), footerTemplate=rodape(),
                                 printBackground=True, preferCSSPageSize=False)
                if "result" not in r:
                    raise SystemExit(str(r))
                pathlib.Path(pdf_path).write_bytes(base64.b64decode(r["result"]["data"]))

        asyncio.run(principal())
    finally:
        proc.terminate()


if __name__ == "__main__":
    imprimir(sys.argv[1], sys.argv[2])
    print("PDF:", sys.argv[2])
