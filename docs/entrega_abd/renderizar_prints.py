"""Transforma cada saída de terminal (evidencias/*.txt) em imagem PNG com aparência de janela de terminal.
As imagens são a saída real dos comandos (nada é digitado à mão); só o enquadramento visual é desenhado.

Uso: python docs/entrega_abd/renderizar_prints.py <pasta_dos_txt> <pasta_dos_png>
"""
import asyncio
import base64
import html
import json
import pathlib
import subprocess
import sys
import textwrap
import time
import urllib.request

import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ENTRADA = pathlib.Path(sys.argv[1])
SAIDA = pathlib.Path(sys.argv[2])
SAIDA.mkdir(parents=True, exist_ok=True)
PORTA = 9334
LARGURA_MAX = 88
CHAR_W, LINE_H = 8.4, 20          # Consolas 14 px

TITULOS = {
    "01_estrutura": "psql - residuos_sinisa",
    "02_tabela_fato": "psql - residuos_sinisa",
    "04_carga": "psql - residuos_sinisa",
    "05_validacao": "psql - residuos_sinisa",
    "06_integridade": "psql - residuos_sinisa",
    "07_views": "psql - residuos_sinisa",
    "08_explain": "psql - residuos_sinisa",
    "09_seguranca": "psql - residuos_sinisa",
    "10_armazenamento": "psql - residuos_sinisa",
    "11_backup_restore": "terminal - backup e restauração",
}


def pagina(titulo, texto):
    linhas = []
    for l in texto.rstrip("\n").split("\n"):
        if l.startswith("\\pset"):
            continue
        # linhas muito longas (ex.: CHECK em \d) são quebradas só para caber na página
        if len(l) > LARGURA_MAX and "|" not in l and "-+-" not in l:
            linhas.extend(textwrap.wrap(l, width=LARGURA_MAX, subsequent_indent="        ",
                                        break_long_words=False, break_on_hyphens=False))
        else:
            linhas.append(l)
    larg = max(len(l) for l in linhas)
    corpo = []
    for l in linhas:
        e = html.escape(l)
        if l.startswith("ERROR:") or l.startswith("psql:"):
            e = f'<span class="erro">{e}</span>'
        elif l.startswith("$ ") or l.startswith("\\"):
            e = f'<span class="cmd">{e}</span>'
        corpo.append(e)
    w = int(max(larg, 40) * CHAR_W + 44)
    h = int(len(linhas) * LINE_H + 78)
    doc = f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;background:#fff}}
.win{{width:{w}px;height:{h}px;box-sizing:border-box;background:#fbfaf7;border:1px solid #bdb6a8;border-radius:6px;overflow:hidden}}
.bar{{height:28px;background:#ece8df;color:#5a564e;font:12.5px Arial,sans-serif;line-height:28px;padding:0 12px 0 64px;border-bottom:1px solid #d3cdc0;position:relative}}
.bar i{{position:absolute;top:9px;width:10px;height:10px;border-radius:50%;background:#c9c2b3}}
pre{{margin:0;padding:12px 20px 16px;color:#23262b;font:14px/{LINE_H}px Consolas,'Cascadia Mono',monospace;white-space:pre}}
.erro{{color:#a32a1a;font-weight:bold}} .cmd{{color:#1f5f4a;font-weight:bold}}
</style><div class="win"><div class="bar"><i style="left:14px"></i><i style="left:30px"></i><i style="left:46px"></i>{html.escape(titulo)}</div><pre>{chr(10).join(corpo)}</pre></div>"""
    return doc, w, h


async def principal():
    perfil = SAIDA / "_perfil_edge"
    proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                             f"--remote-debugging-port={PORTA}", f"--user-data-dir={perfil}",
                             "--allow-file-access-from-files", "about:blank"],
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
        async with websockets.connect(url, max_size=64 * 1024 * 1024) as ws:
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
            for txt in sorted(ENTRADA.glob("*.txt")):
                titulo = TITULOS.get(txt.stem, "terminal")
                doc, w, h = pagina(titulo, txt.read_text(encoding="utf-8"))
                arq = SAIDA / f"{txt.stem}.html"
                arq.write_text(doc, encoding="utf-8")
                await chamar("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=2, mobile=False)
                await chamar("Page.navigate", url=arq.resolve().as_uri())
                await asyncio.sleep(0.8)
                r = await chamar("Page.captureScreenshot", format="png",
                                 clip={"x": 0, "y": 0, "width": w, "height": h, "scale": 1})
                (SAIDA / f"{txt.stem}.png").write_bytes(base64.b64decode(r["result"]["data"]))
                arq.unlink()
                print(txt.stem, w, "x", h)
    finally:
        proc.terminate()


asyncio.run(principal())
