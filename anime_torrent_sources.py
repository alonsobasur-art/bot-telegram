"""Fuentes torrent de anime (castellano / VOSE) para el motor de búsqueda del bot."""

import re
import time
import urllib.parse
from html import unescape

import cloudscraper
import requests
from bs4 import BeautifulSoup

PALABRAS_ES = (
    "castellano",
    "cast",
    "spanish",
    "español",
    "espanol",
    "esp",
    "latino",
    "vose",
    "vos",
    "multi",
    "unionfansub",
    "horriblesubs",
)
PALABRAS_CALIDAD = (
    ("2160", 45),
    ("4k", 45),
    ("1080", 30),
    ("720", 12),
    ("bdrip", 8),
    ("bluray", 10),
    ("webrip", 6),
    ("dual", 15),
)


def _scraper():
    return cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )


def _btih(enlace):
    if not enlace:
        return ""
    m = re.search(r"btih:([a-fA-F0-9]{32,40})", enlace, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    m = re.search(r"btih:([a-zA-Z0-9]{16,40})", enlace)
    return m.group(1).lower() if m else ""


def _limpiar_magnet(magnet):
    magnet = unescape(magnet or "").strip()
    return magnet.split("&tr=")[0] if magnet.startswith("magnet:") else magnet


def puntuar_titulo(titulo):
    bajo = (titulo or "").lower()
    puntos = 0
    if any(p in bajo for p in PALABRAS_ES):
        puntos += 55
    if "sub" in bajo and any(x in bajo for x in ("esp", "cast", "spanish", "español")):
        puntos += 25
    for marca, valor in PALABRAS_CALIDAD:
        if marca in bajo:
            puntos += valor
    if "complete" in bajo or "batch" in bajo or "temporada" in bajo:
        puntos += 5
    return puntos


def _fila_nyaa(scraper, consulta, categoria="1_0", limite=8):
    resultados = []
    q = urllib.parse.quote_plus(consulta)
    url = f"https://nyaa.si/?f=0&c={categoria}&q={q}&s=seeders&o=desc"
    try:
        resp = scraper.get(url, timeout=10)
        if resp.status_code != 200:
            return resultados
        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.select("tr.default, tr.success")[:limite]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            enlaces = cols[1].find_all("a")
            titulo = enlaces[-1].text.strip() if enlaces else ""
            magnet = next(
                (a["href"] for a in cols[2].find_all("a", href=True) if a["href"].startswith("magnet:")),
                None,
            )
            if titulo and magnet:
                resultados.append(
                    {
                        "title": f"🌸 {titulo[:72]}",
                        "magnet": magnet,
                        "source": "Nyaa",
                        "score": puntuar_titulo(titulo),
                        "raw_title": titulo,
                    }
                )
    except Exception:
        pass
    return resultados


def buscar_nyaa_anime(consulta):
    scraper = _scraper()
    vistos = set()
    salida = []
    consultas = [consulta, f"{consulta} castellano", f"{consulta} spanish"]
    for q in consultas:
        for bloque in _fila_nyaa(scraper, q, limite=6):
            h = _btih(bloque["magnet"])
            if h and h not in vistos:
                vistos.add(h)
                salida.append(bloque)
    return salida


def buscar_animetosho(consulta, max_fichas=4):
    scraper = _scraper()
    salida = []
    vistos = set()
    q = urllib.parse.quote_plus(consulta)
    try:
        lista = scraper.get(f"https://animetosho.org/search?q={q}", timeout=12)
        if lista.status_code != 200:
            return salida
        soup = BeautifulSoup(lista.text, "html.parser")
        vistas = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/view/" not in href:
                continue
            if not href.startswith("http"):
                href = "https://animetosho.org" + href
            if href in vistas:
                continue
            vistas.append(href)
            if len(vistas) >= max_fichas:
                break
        for url in vistas:
            try:
                ficha = scraper.get(url, timeout=12)
                if ficha.status_code != 200:
                    continue
                magn = re.findall(r"magnet:\?[^\s\"'<>]+", ficha.text)
                if not magn:
                    continue
                magnet = _limpiar_magnet(magn[0])
                titulo = BeautifulSoup(ficha.text, "html.parser").find("title")
                nombre = (titulo.text.split("|")[0].strip() if titulo else url.split("/")[-1])[:72]
                h = _btih(magnet)
                if not h or h in vistos:
                    continue
                vistos.add(h)
                salida.append(
                    {
                        "title": f"📡 {nombre}",
                        "magnet": magnet,
                        "source": "AnimeTosho",
                        "score": puntuar_titulo(nombre),
                        "raw_title": nombre,
                    }
                )
            except Exception:
                continue
    except Exception:
        pass
    return salida


def buscar_tpb_anime(consulta, browser_headers=None):
    salida = []
    headers = browser_headers or {"User-Agent": "Mozilla/5.0"}
    termino = urllib.parse.quote(f"{consulta} category:507")
    try:
        scraper = _scraper()
        data = scraper.get(f"https://apibay.org/q.php?q={termino}", timeout=10).json()
        if not data or data[0].get("id") == "0":
            termino2 = urllib.parse.quote(f"{consulta} anime castellano")
            data = scraper.get(f"https://apibay.org/q.php?q={termino2}", timeout=10).json()
        if not data or data[0].get("id") == "0":
            return salida
        for t in data[:8]:
            nombre = t.get("name") or "Anime"
            magnet = f"magnet:?xt=urn:btih:{t['info_hash']}&dn={urllib.parse.quote(nombre)}"
            salida.append(
                {
                    "title": f"🏴‍☠️ {nombre[:72]}",
                    "magnet": magnet,
                    "source": "TPB-Anime",
                    "score": puntuar_titulo(nombre),
                    "raw_title": nombre,
                }
            )
    except Exception:
        pass
    return salida


def buscar_elitetorrent_anime(consulta, browser_headers=None):
    """Series en castellano (incluye anime clásico si está indexado)."""
    salida = []
    base = "https://www.elitetorrent.wf"
    headers = browser_headers or {"User-Agent": "Mozilla/5.0"}
    try:
        session = requests.Session()
        session.headers.update(headers)
        resp = session.get(base + "/", params={"s": consulta}, timeout=12)
        if resp.status_code != 200:
            return salida
        vistos = []
        for link in BeautifulSoup(resp.text, "html.parser").find_all("a", href=True):
            href = link["href"]
            if "/series/" not in href and "/peliculas/" not in href:
                continue
            if href in vistos:
                continue
            vistos.append(href)
            if len(vistos) >= 5:
                break
        for href in vistos:
            ficha = session.get(href, timeout=10)
            soup = BeautifulSoup(ficha.text, "html.parser")
            torrent = next(
                (a["href"] for a in soup.find_all("a", href=True) if ".torrent" in a["href"].lower()),
                None,
            )
            if not torrent:
                continue
            if torrent.startswith("/"):
                torrent = base + torrent
            titulo = soup.find("h1")
            title_es = titulo.get_text(" ", strip=True) if titulo else consulta
            bajo = title_es.lower()
            if not any(p in bajo for p in ("anime", "dragon", consulta.lower()[:4])) and "serie" not in bajo:
                if not any(c in bajo for c in ("cast", "anim")):
                    continue
            salida.append(
                {
                    "title": f"🇪🇸 {title_es[:72]}",
                    "magnet": torrent,
                    "source": "EliteTorrent",
                    "score": puntuar_titulo(title_es) + 20,
                    "raw_title": title_es,
                }
            )
    except Exception:
        pass
    return salida


def buscar_todo_anime(consulta, browser_headers=None):
    """Ejecuta todas las fuentes anime y devuelve lista ordenada por relevancia."""
    bloques = []
    bloques.extend(buscar_nyaa_anime(consulta))
    bloques.extend(buscar_animetosho(consulta))
    bloques.extend(buscar_tpb_anime(consulta, browser_headers))
    bloques.extend(buscar_elitetorrent_anime(consulta, browser_headers))
    vistos = set()
    unicos = []
    for item in sorted(bloques, key=lambda x: x.get("score", 0), reverse=True):
        h = _btih(item.get("magnet"))
        if h and h in vistos:
            continue
        if h:
            vistos.add(h)
        unicos.append(item)
    return unicos


def chequeo_rapido():
    """Prueba conectividad básica de cada fuente (sin descargar torrents)."""
    informe = []
    scraper = _scraper()
    pruebas = [
        ("Nyaa", lambda: scraper.get("https://nyaa.si/?f=0&c=1_0&q=test&s=seeders&o=desc", timeout=8)),
        ("AnimeTosho", lambda: scraper.get("https://animetosho.org/search?q=test", timeout=8)),
        ("TPB-Anime", lambda: scraper.get("https://apibay.org/q.php?q=test+category:507", timeout=8)),
        ("EliteTorrent", lambda: requests.get("https://www.elitetorrent.wf/", timeout=8, headers={"User-Agent": "Mozilla/5.0"})),
    ]
    for nombre, llamada in pruebas:
        t0 = time.monotonic()
        ok = False
        detalle = ""
        try:
            r = llamada()
            ok = getattr(r, "status_code", 0) == 200
            detalle = f"HTTP {r.status_code}"
        except Exception as error:
            detalle = str(error)[:80]
        ms = int((time.monotonic() - t0) * 1000)
        informe.append({"name": nombre, "ok": ok, "ms": ms, "detail": detalle})
    return informe
