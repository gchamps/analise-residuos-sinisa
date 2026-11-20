"""Captura as quatro abas do painel Streamlit (http://localhost:8501) com o Edge em modo headless, via protocolo DevTools,
e recorta a área de conteúdo. O painel precisa estar no ar (streamlit run scripts/app.py).
Uso: python docs/entrega_abd/capturar_painel.py <pasta_de_saida>
"""
import asyncio, json, subprocess, time, urllib.request, base64, os, sys
import websockets
EDGE=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT=os.path.abspath(sys.argv[1]) if len(sys.argv)>1 else os.path.abspath(".")   # pasta de saída das capturas
PORT=9333
prof=os.path.join(OUT,"edge_prof")
p=subprocess.Popen([EDGE,"--headless=new","--disable-gpu","--hide-scrollbars",f"--remote-debugging-port={PORT}",f"--user-data-dir={prof}","about:blank"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try:
            tabs=json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json")); break
        except Exception: time.sleep(0.3)
    ws_url=[t for t in tabs if t["type"]=="page"][0]["webSocketDebuggerUrl"]
    async def main():
        async with websockets.connect(ws_url,max_size=64*1024*1024) as ws:
            i=0
            async def call(method,**params):
                nonlocal i; i+=1; mid=i
                await ws.send(json.dumps({"id":mid,"method":method,"params":params}))
                while True:
                    r=json.loads(await ws.recv())
                    if r.get("id")==mid: return r
            async def js(expr):
                r=await call("Runtime.evaluate",expression=expr,returnByValue=True,awaitPromise=True)
                return r.get("result",{}).get("result",{}).get("value")
            async def shot(name,h):
                await call("Emulation.setDeviceMetricsOverride",width=1120,height=h,deviceScaleFactor=2,mobile=False)
                await asyncio.sleep(2.5)
                r=await call("Page.captureScreenshot",format="png")
                open(os.path.join(OUT,name),"wb").write(base64.b64decode(r["result"]["data"]))
            await call("Page.enable")
            await call("Emulation.setDeviceMetricsOverride",width=1120,height=1000,deviceScaleFactor=2,mobile=False)
            await call("Page.navigate",url="http://localhost:8501")
            await asyncio.sleep(9)
            for nome,h in [("Panorama",1900),("Estados",2000),("Municípios",2000),("Método e limitações",2000)]:
                ok=await js("""(()=>{const t=[...document.querySelectorAll('[role=tab]')].find(e=>e.innerText.trim()==%s);if(t){t.click();return true}return false})()"""%json.dumps(nome))
                print(nome,ok)
                await asyncio.sleep(3)
                await shot("dash_"+{"Panorama":"panorama","Estados":"estados","Municípios":"municipios","Método e limitações":"metodo"}[nome]+".png",h)
    asyncio.run(main())
finally:
    p.terminate()


# recortes da área de conteúdo (sem a barra lateral), em pixels da captura (escala 2) -> dash_*_crop.png
from PIL import Image
CORTES = {"dash_panorama": (740, 720, 2100, 2300),      # indicadores principais + gráficos por região
          "dash_estados": (740, 1400, 2100, 2800),      # ranking das UFs
          "dash_municipios": (740, 1396, 2100, 3040)}   # distribuição + início da tabela de municípios
for nome, caixa in CORTES.items():
    Image.open(os.path.join(OUT, nome + ".png")).convert("RGB").crop(caixa).save(os.path.join(OUT, nome + "_crop.png"), optimize=True)
print("recortes gerados")
