"""Malha das UFs (IBGE) para o mapa do dashboard. Não depende de Streamlit."""

import json

# Código IBGE da UF (2 primeiros dígitos do código do município) -> sigla
UF_POR_CODIGO = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
                 "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
                 "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}


def carregar_geojson(caminho):
    """Lê a malha das UFs e inverte a orientação dos contornos (o IBGE usa a convenção oposta à do Vega/d3)."""
    with open(caminho, encoding="utf-8") as f:
        geo = json.load(f)
    for feicao in geo["features"]:
        g = feicao["geometry"]
        poligonos = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poligono in poligonos:
            for anel in poligono:
                anel.reverse()
    return geo


def centro_do_poligono(geometria):
    """Centro do retângulo que envolve a UF (suficiente para posicionar a sigla)."""
    pontos = []

    def coletar(item):
        if isinstance(item[0], (int, float)):
            pontos.append(item)
        else:
            for sub in item:
                coletar(sub)

    coletar(geometria["coordinates"])
    lons = [p[0] for p in pontos]
    lats = [p[1] for p in pontos]
    return (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2


def preparar_mapa(caminho, valores_uf, uf_selecionada, formatar):
    """Devolve (feições com valor e rótulo por UF, siglas com posição) prontas para o Altair."""
    geo = carregar_geojson(caminho)
    feicoes, siglas = [], []
    for f in geo["features"]:
        uf = UF_POR_CODIGO[f["properties"]["codarea"]]
        v = valores_uf.get(uf)
        feicoes.append({"type": "Feature", "geometry": f["geometry"],
                        "properties": {"uf": uf, "valor": v, "sel": uf == uf_selecionada,
                                       "rotulo": formatar(v, 1, "%") if v is not None else "sem dados"}})
        lon, lat = centro_do_poligono(f["geometry"])
        siglas.append({"uf": uf, "lon": lon, "lat": lat})
    return feicoes, siglas
