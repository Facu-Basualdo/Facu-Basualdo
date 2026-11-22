#!/usr/bin/env python3
"""
Genera el README del perfil de GitHub y sus SVG.

El perfil tiene identidad propia, distinta de basualdo.dev:
- el encabezado cuenta la trayectoria como un `git log --graph`, con los
  proyectos en curso como ramas abiertas y los colores de GitHub;
- cada proyecto destacado lleva los colores, la tipografía y algún gesto de su
  propio producto.

GitHub no deja cargar fuentes ni CSS externos en un README, así que cada SVG
lleva incrustado el recorte de las fuentes que usa y sus animaciones.

    pip install fonttools brotli pillow
    python scripts/generar.py
"""
from __future__ import annotations

import base64
import html
import io
import random
import re
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
AQUI = Path(__file__).resolve().parent

# ─── Contenido ──────────────────────────────────────────────────────────────

EMAIL = "facundo@basualdo.dev"
WEB = "https://basualdo.dev"
LINKEDIN = "https://www.linkedin.com/in/facu-basualdo/"
GITHUB = "https://github.com/Facu-Basualdo"

# Colores de cada proyecto para el log: (tema oscuro, tema claro).
COLOR = {
    "mifacu": ("#7aa7ff", "#2552e2"),
    "juegachos": ("#e955ee", "#b80fbb"),
    "brillo": ("#4aa8ff", "#0361bd"),
    "arco": ("#9fbf7a", "#324521"),
}

# De lo más nuevo a lo más viejo. lane 1 y 2 son ramas que siguen abiertas.
COMMITS = [
    {"hash": "17b64f9", "ref": "HEAD", "msg": "Facundo Basualdo · dev full-stack en Resistencia, Chaco", "fecha": "hoy", "lane": 0},
    {"hash": "c4e19a2", "ref": "brillo", "msg": "publiqué Brillo en la Microsoft Store", "fecha": "nov 2026", "lane": 0},
    {"hash": "8b3f0d7", "ref": "juegachos", "msg": "lancé Juegachos: 67 minijuegos open source", "fecha": "jul 2026", "lane": 2},
    {"hash": "5a92e6c", "ref": "arco", "msg": "Arco: gestión de obras con un equipo de 4", "fecha": "may 2026", "lane": 0},
    {"hash": "2f7d4b1", "ref": "mifacu", "msg": "cofundé miFACU: iOS, Android y web", "fecha": "ene 2026", "lane": 1},
    {"hash": "0e1c8a3", "ref": "utn", "msg": "arranqué Ing. en Sistemas en la UTN FRRe", "fecha": "2022", "lane": 0},
]
NOMBRE_REF = {"mifacu": "miFACU", "juegachos": "juegachos", "brillo": "brillo", "arco": "arco", "utn": "tag: utn"}

PROYECTOS = [
    ("mifacu", "https://mifacu.com.ar", "miFACU: plataforma académica en iOS, Android y web"),
    ("juegachos", "https://github.com/Facu-Basualdo/Juegachos", "Juegachos: 67 minijuegos web open source"),
    ("brillo", "https://github.com/Facu-Basualdo/Brillo", "Brillo: control de brillo para Windows, en la Microsoft Store"),
    ("arco", "https://www.arcosoftware.com.ar/", "Arco: software de gestión de obras"),
]

OTROS = [
    ("Vitrina", "https://github.com/Facu-Basualdo/CatalogoTienda"),
    ("El Precioso", "https://github.com/Facu-Basualdo/ElPreciosoTiendaWeb"),
    ("Gestor de Estudios", "https://github.com/Facu-Basualdo/GestorDeEstudios"),
    ("mods de Minecraft", "https://github.com/search?q=user%3AFacu-Basualdo+topic%3Afabric-mod&type=repositories"),
]

# (slug de Simple Icons, nombre)
STACK = [
    ("typescript", "TypeScript"), ("react", "React"), ("nextdotjs", "Next.js"), ("expo", "React Native"),
    ("nodedotjs", "Node.js"), ("postgresql", "PostgreSQL"), ("supabase", "Supabase"), ("redis", "Redis"),
    ("threedotjs", "Three.js"), ("socketdotio", "socket.io"), ("swift", "SwiftUI"), ("dotnet", "C# / .NET"),
    ("tailwindcss", "Tailwind"), ("docker", "Docker"), ("claude", "Claude"), ("vercel", "Vercel"),
]

# ─── Colores de GitHub (Primer) ─────────────────────────────────────────────

GH = {
    "dark": {"panel": "#0d1117", "border": "#30363d", "fg": "#e6edf3", "muted": "#7d8590", "hash": "#d29922",
             "user": "#3fb950", "path": "#58a6ff", "head": "#39c5cf", "main": "#3fb950", "lane": "#484f58",
             "chip": "#161b22"},
    "light": {"panel": "#f6f8fa", "border": "#d0d7de", "fg": "#1f2328", "muted": "#656d76", "hash": "#9a6700",
              "user": "#1a7f37", "path": "#0969da", "head": "#1b7c83", "main": "#1a7f37", "lane": "#afb8c1",
              "chip": "#ffffff"},
}

FLECHA = '<path d="M17 7l-10 10M8 7l9 0l0 9" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'

ANIM_COMUN = """
@keyframes entra{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
@keyframes parpadeo{50%{opacity:0}}
@keyframes titila{0%,100%{opacity:.15}50%{opacity:1}}
@keyframes gira{to{transform:rotate(360deg)}}
@keyframes traza{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.entra{animation:entra .35s ease-out backwards}
.cursor{animation:parpadeo 1s steps(1,end) infinite}
.titila{animation:titila 3s ease-in-out infinite}
.gira{animation:gira 24s linear infinite;transform-box:fill-box;transform-origin:center}
.traza{stroke-dasharray:1;animation:traza 1.2s ease-out backwards}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""

# ─── Fuentes ────────────────────────────────────────────────────────────────


class Fuente:
    def __init__(self, archivo: str, familia: str, ejes: dict | None = None):
        font = TTFont(AQUI / "fuentes" / archivo)
        if ejes and "fvar" in font:
            font = instancer.instantiateVariableFont(font, ejes)
        font.flavor = None
        self.font, self.familia = font, familia
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]
        self.upm = font["head"].unitsPerEm

    def ancho(self, texto: str, tam: float) -> float:
        return sum(self.hmtx[self.cmap.get(ord(c), self.cmap[32])][0] for c in texto) * tam / self.upm

    def css(self, texto: str) -> str:
        buf = io.BytesIO()
        self.font.save(buf)
        buf.seek(0)
        recorte = TTFont(buf)
        opciones = subset.Options()
        opciones.layout_features = ["kern", "liga", "calt"]
        sub = subset.Subsetter(opciones)
        sub.populate(text=texto + " ")
        sub.subset(recorte)
        recorte.flavor = "woff2"
        out = io.BytesIO()
        recorte.save(out)
        datos = base64.b64encode(out.getvalue()).decode()
        return f"@font-face{{font-family:'{self.familia}';src:url(data:font/woff2;base64,{datos}) format('woff2')}}"


MONO = Fuente("GeistMono-latin.woff2", "GMono", {"wght": 400})
MONO_B = Fuente("GeistMono-latin.woff2", "GMonoB", {"wght": 600})
GEIST = Fuente("Geist.woff2", "Geist", {"wght": 400})
GEIST_B = Fuente("Geist.woff2", "GeistB", {"wght": 700})
ARCHIVO = Fuente("Archivo-BlackItalic.woff2", "ArchivoBlack")
INTER = Fuente("Inter.woff2", "Inter", {"wght": 400})
INTER_B = Fuente("Inter.woff2", "InterB", {"wght": 700})
# Brillo es una app de Windows: usa la letra del sistema, sin incrustar.
SEGOE = "'Segoe UI Variable Display','Segoe UI',system-ui,-apple-system,sans-serif"


def esc(texto: str) -> str:
    return html.escape(texto, quote=True)


def png(nombre: str) -> str:
    return "data:image/png;base64," + base64.b64encode((AQUI / "logos" / f"{nombre}.png").read_bytes()).decode()


class Svg:
    def __init__(self, ancho: float, alto: float, titulo: str):
        self.ancho, self.alto, self.titulo = ancho, alto, titulo
        self.defs: list[str] = []
        self.partes: list[str] = []
        self.usado: dict[Fuente, set[str]] = {}
        self.css_extra = ""

    def t(self, x, y, texto, tam, fuente: Fuente | str, color, ancla="start", extra=""):
        if isinstance(fuente, Fuente):
            self.usado.setdefault(fuente, set()).update(texto)
            familia = f"'{fuente.familia}'"
        else:
            familia = fuente
        a = f' text-anchor="{ancla}"' if ancla != "start" else ""
        self.partes.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{esc(familia)}" font-size="{tam}" fill="{color}"{a} {extra}>{esc(texto)}</text>'
        )

    def add(self, svg: str):
        self.partes.append(svg)

    def render(self) -> str:
        css = "".join(f.css("".join(sorted(c))) for f, c in self.usado.items())
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.ancho:.0f}" height="{self.alto:.0f}" '
            f'viewBox="0 0 {self.ancho:.0f} {self.alto:.0f}" role="img" aria-label="{esc(self.titulo)}">'
            f"<title>{esc(self.titulo)}</title><style>{css}text{{white-space:pre}}{ANIM_COMUN}{self.css_extra}</style>"
            f'<defs>{"".join(self.defs)}</defs>{"".join(self.partes)}</svg>'
        )


def envolver(texto: str, max_ancho: float, fuente: Fuente, tam: float) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if actual and fuente.ancho(prueba, tam) > max_ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    return lineas + ([actual] if actual else [])


def flecha(x, y, tam, color, ancho_trazo=2) -> str:
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({tam / 24:.3f})" stroke="{color}" '
            f'stroke-width="{ancho_trazo}">{FLECHA}</g>')


# ─── Encabezado: git log --graph ────────────────────────────────────────────

W = 840


def encabezado(tema: str) -> str:
    c = GH[tema]
    oscuro = tema == "dark"
    fila, y0, tam = 34, 84, 13
    alto = y0 + fila * (len(COMMITS) - 1) + 70
    s = Svg(W, alto, "git log de Facundo Basualdo: " + "; ".join(f"{k['fecha']}: {k['msg']}" for k in COMMITS))
    s.add(f'<rect x=".5" y=".5" width="{W - 1}" height="{alto - 1}" rx="12" fill="{c["panel"]}" stroke="{c["border"]}"/>')

    def prompt(y, comando, retraso, cursor=False):
        x = 28
        s.add(f'<g class="entra" style="animation-delay:{retraso}s">')
        for texto, color in [("facu@basualdo", c["user"]), (":", c["fg"]), ("~", c["path"]), ("$ ", c["fg"])]:
            s.t(x, y, texto, tam, MONO_B if color != c["fg"] else MONO, color)
            x += MONO.ancho(texto, tam)
        if comando:
            s.t(x, y, comando, tam, MONO, c["fg"])
            x += MONO.ancho(comando, tam)
        if cursor:
            s.add(f'<rect class="cursor" x="{x + 2:.1f}" y="{y - 11}" width="8" height="15" fill="{c["fg"]}"/>')
        s.add("</g>")

    prompt(40, "git log --graph --oneline --since=2022", 0.1)

    # Grafo: rieles por rama y curvas donde nace cada una.
    lx = lambda lane: 38 + lane * 20
    yf = lambda i: y0 + i * fila - 4.5
    color_ref = lambda ref: c["fg"] if ref == "HEAD" else (COLOR[ref][0 if oscuro else 1] if ref in COLOR else c["muted"])
    ramas = {1: "mifacu", 2: "juegachos"}
    s.add(f'<path class="traza" pathLength="1" d="M{lx(0)} {yf(0)} V{yf(len(COMMITS) - 1)}" stroke="{c["lane"]}" stroke-width="2" fill="none"/>')
    for i, k in enumerate(COMMITS):
        if k["lane"]:
            padre = yf(i + 1)
            d = (f"M{lx(0)} {padre} C{lx(0)} {padre - fila / 2} {lx(k['lane'])} {yf(i) + fila / 2} {lx(k['lane'])} {yf(i)} "
                 f"V{yf(0)}")
            s.add(f'<path class="traza" pathLength="1" style="animation-delay:{0.3 + i * 0.1:.2f}s" d="{d}" '
                  f'stroke="{color_ref(ramas[k["lane"]])}" stroke-width="2" fill="none"/>')
    # Las ramas abiertas también tienen un commit arriba: siguen en curso.
    for lane, ref in ramas.items():
        s.add(f'<circle class="entra" style="animation-delay:1.2s" cx="{lx(lane)}" cy="{yf(0)}" r="4" fill="{c["panel"]}" '
              f'stroke="{color_ref(ref)}" stroke-width="2"/>')

    x_txt = lx(2) + 30
    for i, k in enumerate(COMMITS):
        y = y0 + i * fila
        col = color_ref(k["ref"])
        s.add(f'<g class="entra" style="animation-delay:{0.25 + i * 0.12:.2f}s">')
        if k["ref"] == "HEAD":
            s.add(f'<circle cx="{lx(0)}" cy="{yf(i)}" r="6" fill="{c["fg"]}"/>'
                  f'<circle cx="{lx(0)}" cy="{yf(i)}" r="10" fill="none" stroke="{c["fg"]}" stroke-opacity=".25" stroke-width="2"/>')
        else:
            s.add(f'<circle cx="{lx(k["lane"])}" cy="{yf(i)}" r="5" fill="{col}"/>')
        x = x_txt
        s.t(x, y, k["hash"], tam, MONO, c["hash"])
        x += MONO.ancho(k["hash"] + " ", tam)
        if k["ref"] == "HEAD":
            partes = [("(", c["hash"], MONO), ("HEAD", c["head"], MONO_B), (" -> ", c["hash"], MONO),
                      ("main", c["main"], MONO_B), (") ", c["hash"], MONO)]
        else:
            partes = [("(", c["hash"], MONO), (NOMBRE_REF[k["ref"]], col, MONO_B), (") ", c["hash"], MONO)]
        for texto, color, fuente in partes:
            s.t(x, y, texto, tam, fuente, color)
            x += MONO.ancho(texto, tam)
        s.t(x, y, k["msg"], tam, MONO_B if k["ref"] == "HEAD" else MONO, c["fg"])
        s.t(W - 28, y, k["fecha"], 12, MONO, c["muted"], ancla="end")
        s.add("</g>")

    prompt(alto - 26, "", 0.25 + len(COMMITS) * 0.12 + 0.1, cursor=True)
    return s.render()


# ─── Tarjetas de proyectos, cada una con su identidad ───────────────────────

CW, CH = 412, 248


def pildora(s: Svg, x, y, texto, fuente, tam, color_txt, fondo=None, borde=None, rx=999, pad=11, alto=24) -> float:
    w = fuente.ancho(texto, tam) + 2 * pad
    attrs = f'fill="{fondo or "none"}"' + (f' stroke="{borde}"' if borde else "")
    s.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{alto}" rx="{min(rx, alto / 2)}" {attrs}/>')
    s.t(x + pad, y + alto / 2 + tam * 0.36, texto, tam, fuente, color_txt)
    return w


def tarjeta_mifacu() -> str:
    s = Svg(CW, CH, PROYECTOS[0][2])
    s.defs.append(
        '<linearGradient id="fondo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2552e2"/>'
        '<stop offset="1" stop-color="#3863f5"/></linearGradient>'
        '<radialGradient id="luz" cx=".9" cy=".05" r=".7"><stop offset="0" stop-color="#7aa7ff" stop-opacity=".55"/>'
        '<stop offset="1" stop-color="#7aa7ff" stop-opacity="0"/></radialGradient>'
        f'<clipPath id="borde"><rect width="{CW}" height="{CH}" rx="16"/></clipPath>'
    )
    s.add('<g clip-path="url(#borde)">')
    s.add(f'<rect width="{CW}" height="{CH}" fill="url(#fondo)"/><rect width="{CW}" height="{CH}" fill="url(#luz)"/>')
    # Hoja rayada de cuaderno.
    s.add("".join(f'<rect x="0" y="{y}" width="{CW}" height="1" fill="#fff" fill-opacity=".07"/>' for y in range(104, CH, 24)))
    s.add('<rect x="70" y="92" width="1" height="200" fill="#ff8fa3" fill-opacity=".3"/>')
    s.add("</g>")
    s.add(f'<circle cx="50" cy="50" r="27" fill="#fff" fill-opacity=".18"/><image href="{png("mifacu")}" x="26" y="26" width="48" height="48"/>')
    s.t(90, 47, "miFACU", 28, GEIST_B, "#fff")
    s.t(91, 68, "Plataforma académica · cofundador", 13, GEIST, "#fff", extra='fill-opacity=".78"')
    y = 122
    for linea in envolver("Materias, correlativas, horarios y finales en un solo lugar, con IA para estudiar.", CW - 108, GEIST, 14.5):
        s.t(84, y, linea, 14.5, GEIST, "#fff", extra='fill-opacity=".92"')
        y += 24
    x = 84
    for p in ["App Store", "Google Play", "Web"]:
        x += pildora(s, x, CH - 66, p, GEIST_B, 12, "#fff", fondo="#ffffff26") + 6
    s.t(24, CH - 20, "mifacu.com.ar", 13, GEIST_B, "#fff")
    s.add(flecha(24 + GEIST_B.ancho("mifacu.com.ar", 13) + 4, CH - 32, 14, "#fff"))
    return s.render()


def tarjeta_juegachos() -> str:
    s = Svg(CW, CH, PROYECTOS[1][2])
    s.defs.append(
        '<radialGradient id="g1" cx="1" cy="0" r=".9"><stop offset="0" stop-color="#e519e7" stop-opacity=".5"/><stop offset="1" stop-color="#e519e7" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="g2" cx="0" cy="1" r=".8"><stop offset="0" stop-color="#25e4f8" stop-opacity=".32"/><stop offset="1" stop-color="#25e4f8" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="neon" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff4ff8"/><stop offset="1" stop-color="#25e4f8"/></linearGradient>'
        '<linearGradient id="marco" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e519e7"/><stop offset="1" stop-color="#25e4f8"/></linearGradient>'
        '<filter id="brillo" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>'
        f'<clipPath id="borde"><rect width="{CW}" height="{CH}" rx="16"/></clipPath>'
    )
    s.add('<g clip-path="url(#borde)">')
    s.add(f'<rect width="{CW}" height="{CH}" fill="#0b031a"/><rect width="{CW}" height="{CH}" fill="url(#g1)"/><rect width="{CW}" height="{CH}" fill="url(#g2)"/>')
    rnd = random.Random(5)
    estrellas = []
    while len(estrellas) < 22:
        x, y, l = rnd.uniform(10, CW - 10), rnd.uniform(10, CH - 10), rnd.choice([2, 2, 3])
        # Que no caigan sobre el logo ni el texto.
        if (x < 350 and 16 < y < 92) or (14 < x < CW - 14 and 96 < y < CH - 8):
            continue
        col = rnd.choice(["#ffffff", "#25e4f8", "#ff4ff8", "#ffd700"])
        estrellas.append(f'<rect class="titila" x="{x:.0f}" y="{y:.0f}" width="{l}" height="{l}" fill="{col}" '
                         f'style="animation-delay:{rnd.uniform(0, 3):.2f}s;animation-duration:{rnd.uniform(2, 4.5):.2f}s"/>')
    s.add("".join(estrellas))
    s.add("</g>")
    s.add(f'<rect x=".75" y=".75" width="{CW - 1.5}" height="{CH - 1.5}" rx="15.5" fill="none" stroke="url(#marco)" stroke-width="1.5"/>')
    s.add(f'<image href="{png("juegachos")}" x="24" y="24" width="50" height="50"/>')
    s.t(88, 58, "JUEGACHOS", 31, ARCHIVO, "url(#neon)", extra='filter="url(#brillo)" opacity=".8"')
    s.t(88, 58, "JUEGACHOS", 31, ARCHIVO, "url(#neon)")
    s.t(90, 80, "> 67 minijuegos · open source", 12, MONO, "#25e4f8")
    y = 120
    for linea in envolver("Ranking global y salas multijugador de hasta 8 personas, en el navegador. ¿Tenés una idea? Sumá tu juego con un PR.", CW - 48, MONO, 12.5):
        s.t(24, y, linea, 12.5, MONO, "#ece6ff", extra='fill-opacity=".88"')
        y += 21
    x = 24
    for texto, col in [("67 juegos", "#ff4ff8"), ("8 jugadores", "#25e4f8"), ("3D + 2D", "#ffd700")]:
        x += pildora(s, x, CH - 70, texto, MONO_B, 11.5, col, borde=col, rx=4) + 8
    s.add(f'<path d="M24 {CH - 31} l9 5.5 l-9 5.5 z" fill="#25e4f8"/>')
    s.t(40, CH - 20, "JUGAR en juegachos.com", 12.5, MONO_B, "#25e4f8")
    s.t(CW - 24, CH - 20, "8 colaboradores", 12, MONO, "#ece6ff", ancla="end", extra='fill-opacity=".6"')
    return s.render()


def tarjeta_brillo() -> str:
    s = Svg(CW, CH, PROYECTOS[2][2])
    s.defs.append(
        '<linearGradient id="fondo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0260bc"/><stop offset="1" stop-color="#2492ed"/></linearGradient>'
        '<radialGradient id="bloom" cx=".85" cy=".15" r=".6"><stop offset="0" stop-color="#bfe3ff" stop-opacity=".55"/><stop offset="1" stop-color="#bfe3ff" stop-opacity="0"/></radialGradient>'
        f'<clipPath id="borde"><rect width="{CW}" height="{CH}" rx="16"/></clipPath>'
    )
    s.add('<g clip-path="url(#borde)">')
    s.add(f'<rect width="{CW}" height="{CH}" fill="url(#fondo)"/><rect width="{CW}" height="{CH}" fill="url(#bloom)"/>')
    # Sol que gira despacio.
    rayos = "".join(
        f'<rect x="-3" y="-62" width="6" height="18" rx="3" fill="#fff" transform="rotate({a})"/>' for a in range(0, 360, 45))
    s.add(f'<g transform="translate({CW - 58} 46) scale(.78)"><g class="gira"><circle r="30" fill="#fff" fill-opacity=".95"/>{rayos}</g></g>')
    s.add("</g>")
    s.t(24, 52, "Brillo", 30, SEGOE, "#fff", extra='font-weight="600"')
    s.t(25, 75, "Control de brillo para Windows", 14, SEGOE, "#fff", extra='fill-opacity=".85"')
    # Panel tipo flyout de Windows 11 con dos monitores.
    fx, fy, fw, fh = 24, 96, CW - 48, 96
    s.add(f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="8" fill="#202020" fill-opacity=".9" stroke="#ffffff" stroke-opacity=".08"/>')
    for i, (nombre, desde, hasta, dur) in enumerate([("Monitor 1", 0.72, 0.35, 5), ("Laptop", 0.4, 0.85, 6.5)]):
        y = fy + 32 + i * 38
        s.t(fx + 16, y + 4, nombre, 12, SEGOE, "#fff", extra='fill-opacity=".85"')
        tx, tw = fx + 100, fw - 170
        s.add(f'<rect x="{tx}" y="{y - 2}" width="{tw}" height="4" rx="2" fill="#9a9a9a" fill-opacity=".5"/>')
        a, b = tx + tw * desde, tx + tw * hasta
        vals = f"{a:.1f};{b:.1f};{a:.1f}"
        anim = f'dur="{dur}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".4 0 .2 1;.4 0 .2 1"'
        s.add(f'<rect x="{tx}" y="{y - 2}" width="{a - tx:.1f}" height="4" rx="2" fill="#4cc2ff">'
              f'<animate attributeName="width" values="{a - tx:.1f};{b - tx:.1f};{a - tx:.1f}" {anim}/></rect>')
        s.add(f'<circle cx="{a:.1f}" cy="{y}" r="9" fill="#454545"><animate attributeName="cx" values="{vals}" {anim}/></circle>'
              f'<circle cx="{a:.1f}" cy="{y}" r="5" fill="#4cc2ff"><animate attributeName="cx" values="{vals}" {anim}/></circle>')
        # Ícono de sol chico a la derecha.
        s.add(f'<circle cx="{fx + fw - 22}" cy="{y}" r="4" fill="none" stroke="#fff" stroke-width="1.5" stroke-opacity=".8"/>')
    s.t(24, CH - 20, "Microsoft Store", 13.5, SEGOE, "#fff", extra='font-weight="600"')
    s.add(flecha(24 + 104, CH - 32, 14, "#fff"))
    s.t(CW - 24, CH - 20, "C# · DDC/CI · WMI", 12, SEGOE, "#fff", ancla="end", extra='fill-opacity=".75"')
    return s.render()


def tarjeta_arco() -> str:
    s = Svg(CW, CH, PROYECTOS[3][2])
    oliva = "#324521"
    s.defs.append(
        '<pattern id="fina" width="12" height="12" patternUnits="userSpaceOnUse"><path d="M12 0H0V12" fill="none" stroke="#324521" stroke-opacity=".07"/></pattern>'
        '<pattern id="gruesa" width="48" height="48" patternUnits="userSpaceOnUse"><path d="M48 0H0V48" fill="none" stroke="#324521" stroke-opacity=".13"/></pattern>'
        f'<clipPath id="borde"><rect width="{CW}" height="{CH}" rx="16"/></clipPath>'
    )
    s.add('<g clip-path="url(#borde)">')
    s.add(f'<rect width="{CW}" height="{CH}" fill="#f6f7f2"/><rect width="{CW}" height="{CH}" fill="url(#fina)"/><rect width="{CW}" height="{CH}" fill="url(#gruesa)"/>')
    # Cota de plano arriba a la derecha.
    x1, x2, yc = CW - 150, CW - 24, 30
    s.add(f'<g stroke="{oliva}" stroke-opacity=".55" stroke-width="1"><path d="M{x1} {yc}H{x2}M{x1} {yc - 6}V{yc + 6}M{x2} {yc - 6}V{yc + 6}"/>'
          f'<path d="M{x1} {yc}l6 -3v6z M{x2} {yc}l-6 -3v6z" fill="{oliva}" fill-opacity=".55"/></g>')
    s.t((x1 + x2) / 2, yc - 6, "12,40 m", 10.5, MONO, oliva, ancla="middle", extra='fill-opacity=".7"')
    s.add("</g>")
    s.add(f'<rect x=".5" y=".5" width="{CW - 1}" height="{CH - 1}" rx="15.5" fill="none" stroke="#d6dacb"/>')
    s.add(f'<rect x="24" y="24" width="48" height="48" rx="12" fill="#fff" stroke="#e1e4d8"/><image href="{png("arco")}" x="33" y="33.5" width="30" height="28.4"/>')
    s.t(86, 50, "Arco", 28, INTER_B, "#111")
    s.t(87, 70, "Software de gestión de obras", 13, INTER, "#55594d")
    y = 112
    for linea in envolver("Avance ponderado, planos con versiones, presupuestos y certificados desde Excel. Toda la seguridad en Row Level Security.", CW - 48, INTER, 13.5):
        s.t(24, y, linea, 13.5, INTER, "#2b2e26")
        y += 21
    # Barra de avance de obra.
    by = y + 4
    s.t(24, by + 4, "Avance de obra", 11.5, INTER, "#55594d")
    bx, bw = 130, CW - 24 - 130 - 40
    s.add(f'<rect x="{bx}" y="{by - 4}" width="{bw}" height="8" rx="4" fill="{oliva}" fill-opacity=".12"/>'
          f'<rect x="{bx}" y="{by - 4}" width="{bw * 0.68:.1f}" height="8" rx="4" fill="{oliva}">'
          f'<animate attributeName="width" from="0" to="{bw * 0.68:.1f}" dur="1.6s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 0 .2 1"/></rect>')
    s.t(CW - 24, by + 4, "68%", 11.5, INTER_B, oliva, ancla="end")
    s.t(24, CH - 20, "arcosoftware.com.ar", 13, INTER_B, oliva)
    s.add(flecha(24 + INTER_B.ancho("arcosoftware.com.ar", 13) + 4, CH - 32, 14, oliva))
    s.t(CW - 24, CH - 20, "equipo de 4", 12, INTER, "#55594d", ancla="end")
    return s.render()


TARJETAS = {"mifacu": tarjeta_mifacu, "juegachos": tarjeta_juegachos, "brillo": tarjeta_brillo, "arco": tarjeta_arco}

# ─── Stack ──────────────────────────────────────────────────────────────────


def luminancia(hex_: str) -> float:
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def stack(tema: str) -> str:
    c = GH[tema]
    piezas, x, y, alto, sep = [], 0.0, 0.0, 36, 8
    for slug, nombre in STACK:
        svg = (AQUI / "iconos" / f"{slug}.svg").read_text(encoding="utf-8")
        d = re.search(r'<path d="([^"]+)"', svg).group(1)
        color = re.search(r'fill="(#[0-9A-Fa-f]{6})"', svg).group(1)
        if tema == "dark" and luminancia(color) < 0.2:
            color = c["fg"]
        w = 14 + 18 + 9 + MONO.ancho(nombre, 12.5) + 14
        if x and x + w > W:
            x, y = 0, y + alto + sep
        piezas.append((x, y, w, d, color, nombre))
        x += w + sep
    s = Svg(W, y + alto + 1, "Stack: " + ", ".join(n for _, n in STACK))
    for i, (x, y, w, d, color, nombre) in enumerate(piezas):
        s.add(f'<g class="entra" style="animation-delay:{i * 0.04:.2f}s">')
        s.add(f'<rect x="{x + .5:.1f}" y="{y + .5:.1f}" width="{w - 1:.1f}" height="{alto - 1}" rx="{alto / 2}" fill="{c["chip"]}" stroke="{c["border"]}"/>')
        s.add(f'<path transform="translate({x + 14:.1f} {y + 9}) scale(.75)" d="{d}" fill="{color}"/>')
        s.t(x + 41, y + alto / 2 + 4.5, nombre, 12.5, MONO, c["fg"])
        s.add("</g>")
    return s.render()


# ─── README ─────────────────────────────────────────────────────────────────


def imagen(nombre: str, alt: str, ancho: str, temas=True) -> str:
    if not temas:
        return f'<img src="./assets/{nombre}.svg" alt="{esc(alt)}" width="{ancho}" />'
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="./assets/{nombre}-dark.svg" />'
            f'<img src="./assets/{nombre}-light.svg" alt="{esc(alt)}" width="{ancho}" /></picture>')


SNAKE = "https://raw.githubusercontent.com/Facu-Basualdo/Facu-Basualdo/output/github-contribution-grid-snake"


def readme() -> str:
    tarjetas = []
    for i in range(0, len(PROYECTOS), 2):
        tarjetas.append("<p>\n" + "\n".join(
            f'  <a href="{href}">{imagen(f"proyecto-{pid}", alt, "49%", temas=False)}</a>'
            for pid, href, alt in PROYECTOS[i:i + 2]) + "\n</p>")
    otros = " · ".join(f"[{n}]({u})" for n, u in OTROS)
    return f"""<a href="{WEB}">{imagen("encabezado", "git log de Facundo Basualdo: dev full-stack en Resistencia, Chaco. Cofundador de miFACU, creador de Juegachos, autor de Brillo y parte del equipo de Arco.", "100%")}</a>

### Hola, soy Facu 👋

Estudio Ingeniería en Sistemas en la UTN FRRe y me gusta construir cosas que la gente use de verdad: apps en las tiendas, juegos que se juegan con amigos y herramientas que resuelven una molestia concreta.

- 🛠️ Ahora mismo: **miFACU** como cofundador y **Juegachos** como maintainer.
- 🎮 Juegachos es open source: si tenés una idea de juego, [mandá un PR]({PROYECTOS[1][1]}).
- 🧠 Me interesan la IA aplicada, el tiempo real y los gráficos en el navegador.
- 📫 [{EMAIL}](mailto:{EMAIL}) · [basualdo.dev]({WEB}) · [LinkedIn]({LINKEDIN})

### 📌 Proyectos

{chr(10).join(tarjetas)}

<sub>También hice: {otros}</sub>

### 🧰 Stack

{imagen("stack", "Stack: " + ", ".join(n for _, n in STACK), "100%")}

### 🐍 Actividad

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="{SNAKE}-dark.svg" />
  <img alt="Mis contribuciones en GitHub" src="{SNAKE}.svg" width="100%" />
</picture>

<!-- Generado con scripts/generar.py: editá los datos ahí y volvé a correrlo. -->
"""


def main():
    ASSETS.mkdir(exist_ok=True)
    for viejo in ASSETS.glob("*"):
        viejo.unlink()
    archivos = {}
    for tema in GH:
        archivos[f"encabezado-{tema}"] = encabezado(tema)
        archivos[f"stack-{tema}"] = stack(tema)
    for pid, fn in TARJETAS.items():
        archivos[f"proyecto-{pid}"] = fn()
    for nombre, contenido in archivos.items():
        (ASSETS / f"{nombre}.svg").write_text(contenido, encoding="utf-8")
    (RAIZ / "README.md").write_text(readme(), encoding="utf-8")
    total = sum(len(c.encode()) for c in archivos.values())
    print(f"{len(archivos)} SVG ({total / 1024:.0f} KB) y README.md generados.")


if __name__ == "__main__":
    main()
