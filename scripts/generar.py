#!/usr/bin/env python3
"""
Genera el README del perfil y sus SVG con el mismo estilo que basualdo.dev:
negro puro, blanco como único acento, esquinas rectas, Geist Pixel para lo que
tiene que llamar la atención y Geist Mono para todo lo demás.

GitHub no deja cargar fuentes ni CSS externos en un README, así que cada SVG
lleva incrustada la parte de las fuentes que usa (recortada a sus caracteres) y
sus animaciones en CSS/SMIL. Cada imagen sale en versión oscura y clara.

    pip install fonttools brotli
    python scripts/generar.py

Para actualizar el perfil se tocan los datos de abajo (copiados de
Portafolio/src/data/perfil.ts) y se vuelve a correr el script.
"""
from __future__ import annotations

import base64
import html
import io
import random
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"
FUENTES = Path(__file__).resolve().parent / "fuentes"

# ─── Contenido ──────────────────────────────────────────────────────────────

PERFIL = {
    "nombre": ["Facundo", "Basualdo"],
    "roles": ["full-stack", "de producto", "de IA aplicada", "de tiempo real"],
    "ubicacion": "Resistencia, Chaco, Argentina",
    "resumen": (
        "Estudio Ingeniería en Sistemas en la UTN FRRE y construyo productos que están en "
        "producción: una plataforma académica en Google Play y web, una plataforma open source "
        "de minijuegos con aportes de la comunidad y una utilidad para Windows en la Microsoft Store."
    ),
    "disponibilidad": "Disponible para trabajo remoto o presencial en Resistencia · UTC-3",
    "email": "facundo@basualdo.dev",
    "web": "https://basualdo.dev",
    "linkedin": "https://www.linkedin.com/in/facu-basualdo/",
    "cv": "https://basualdo.dev/cv-facundo-basualdo.pdf",
}

CIFRAS = [
    ("~230k", "líneas en miFACU"),
    ("67", "juegos en Juegachos"),
    ("8", "colaboradores open source"),
    ("3", "plataformas en producción"),
]

# destino: a dónde lleva el clic en la tarjeta (el repo si es público).
PROYECTOS = [
    {
        "id": "mifacu",
        "nombre": "miFACU",
        "bajada": "Plataforma académica en iOS, Android y web",
        "descripcion": "Gestor académico para universitarios: materias, correlativas, horarios, finales, apuntes e IA de estudio, con panel de administración y modelo freemium.",
        "destacados": [
            "Monorepo de 4 plataformas: API Node/Express, web Next.js 16, React Native y app iOS nativa en SwiftUI.",
            "IA con cadenas de fallback entre Gemini, Claude, DeepSeek y OpenAI según costo, latencia o calidad.",
        ],
        "stack": ["Next.js", "React Native", "SwiftUI", "Node.js", "PostgreSQL", "Redis", "Vercel AI SDK"],
        "rol": "Cofundador · full-stack",
        "periodo": "2026 – hoy",
        "enlaces": ["mifacu.com.ar", "App Store", "Google Play"],
        "destino": "https://mifacu.com.ar",
    },
    {
        "id": "juegachos",
        "nombre": "Juegachos",
        "bajada": "67 minijuegos web, open source",
        "descripcion": "Colección de minijuegos jugables en el navegador con ranking global, salas multijugador de hasta 8 personas y aportes de la comunidad vía Pull Request.",
        "destacados": [
            "Arquitectura de plugins auto-descubiertos: sumar un juego no toca código compartido.",
            "Salas host-autoritativas sobre Supabase Realtime y 17 juegos 3D con Three.js y Rapier.",
        ],
        "stack": ["TypeScript", "Three.js", "Supabase", "socket.io", "Vite", "Playwright"],
        "rol": "Creador y maintainer",
        "periodo": "2026 – hoy",
        "enlaces": ["juegachos.com", "Código"],
        "destino": "https://github.com/Facu-Basualdo/Juegachos",
    },
    {
        "id": "brillo",
        "nombre": "Brillo",
        "bajada": "Control de brillo para Windows, en la Microsoft Store",
        "descripcion": "Cambia el brillo de cada pantalla desde un icono junto al reloj o con un atajo global, sin tocar los botones del monitor.",
        "destacados": [
            "Monitores externos por DDC/CI (dxva2 vía P/Invoke) y la laptop por WMI.",
            "Paquete MSIX para la Store e instalador sin permisos de administrador.",
        ],
        "stack": ["C#", "WinForms", "Win32", "DDC/CI", "MSIX"],
        "rol": "Proyecto propio",
        "periodo": "Nov 2026",
        "enlaces": ["Microsoft Store", "Código"],
        "destino": "https://github.com/Facu-Basualdo/Brillo",
    },
    {
        "id": "arco",
        "nombre": "Arco",
        "bajada": "Software de gestión de obras",
        "descripcion": "Proyectos, actividades con avance ponderado, planos con observaciones, presupuestos, certificados e informes. Toda la seguridad está en Row Level Security.",
        "destacados": [
            "Módulo de planos y documentos con carpetas, versiones y visor PDF.",
            "Importación de presupuestos y certificados desde Excel.",
        ],
        "stack": ["Next.js", "Supabase", "HeroUI", "RLS", "exceljs"],
        "rol": "Full-stack · equipo de 4",
        "periodo": "May – Ago 2026",
        "enlaces": ["arcosoftware.com.ar"],
        "destino": "https://www.arcosoftware.com.ar/",
    },
    {
        "id": "vitrina",
        "nombre": "Vitrina",
        "bajada": "Tienda online con catálogo genérico",
        "descripcion": "Sirve igual para ropa que para electrónica: filtros facetados, variantes con stock propio y pedidos por WhatsApp con el total calculado en la base.",
        "destacados": [
            "Promociones, combos y cupones evaluados en PostgreSQL, sin acumularse.",
            "Punto de venta de escritorio en Python + PySide6 sobre la misma base.",
        ],
        "stack": ["Next.js", "HeroUI", "Supabase", "TipTap", "Python"],
        "rol": "Proyecto propio",
        "periodo": "2026",
        "enlaces": ["vitrina.basualdo.dev", "Código"],
        "destino": "https://github.com/Facu-Basualdo/CatalogoTienda",
    },
    {
        "id": "el-precioso",
        "nombre": "El Precioso",
        "bajada": "Tienda online para un emprendimiento local",
        "descripcion": "Catálogo pensado para el celular, carrito que termina en un pedido por WhatsApp y un panel para que la dueña maneje todo desde el teléfono.",
        "destacados": [
            "Editor de fotos que quita el fondo en el navegador con un modelo ONNX.",
            "Cotización, promociones y cupones calculados en PostgreSQL, con RLS.",
        ],
        "stack": ["Next.js", "Supabase", "HeroUI", "RLS", "ONNX"],
        "rol": "Full-stack · para un emprendimiento",
        "periodo": "May – Nov 2026",
        "enlaces": ["Código"],
        "destino": "https://github.com/Facu-Basualdo/ElPreciosoTiendaWeb",
    },
    {
        "id": "gestor-de-estudios",
        "nombre": "Gestor de Estudios",
        "bajada": "Tutor de estudio con IA",
        "descripcion": "Vault de Obsidian que arma, conduce y registra sesiones de estudio con Claude Code como tutor, más una web de flashcards y cuestionarios generados desde las notas.",
        "destacados": [
            "Priorización por peso × dominio × urgencia.",
            "Recuperación activa y repetición espaciada.",
        ],
        "stack": ["Next.js", "Claude Code", "Gemini", "Obsidian"],
        "rol": "Proyecto propio",
        "periodo": "2026",
        "enlaces": ["tutor.basualdo.dev", "Código"],
        "destino": "https://github.com/Facu-Basualdo/GestorDeEstudios",
    },
    {
        "id": "mods-minecraft",
        "nombre": "Mods de Minecraft",
        "bajada": "Cuatro mods de Fabric que se juegan juntos",
        "descripcion": "Bloodmoon & Bosses sube el nivel de los mobs, Hero's Forge te deja comprar estadísticas con experiencia, Mythic Loot suelta equipo con rareza y Soul Link comparte inventario y hambre entre jugadores.",
        "destacados": [],
        "stack": ["Java", "Fabric", "Minecraft 26.3"],
        "rol": "Proyecto propio",
        "periodo": "2026",
        "enlaces": ["Soul Link", "Hero's Forge", "Mythic Loot", "Bloodmoon"],
        "destino": "https://github.com/search?q=user%3AFacu-Basualdo+topic%3Afabric-mod&type=repositories",
    },
]

EXPERIENCIA = [
    ("Jul 2026", "Creador y maintainer", "Juegachos · open source · jul 2026 – hoy", [
        "314 de 425 commits y revisión de los aportes de 8 colaboradores.",
        "Guía de contribución y documentación por juego para que cualquiera pueda sumar el suyo.",
    ]),
    ("May 2026", "Desarrollador full-stack", "Arco · equipo de 4 · may – ago 2026", [
        "Aplicación de gestión de obras con ~52.000 líneas y 84 migraciones SQL, con seguridad íntegramente en RLS.",
        "Reduje el tiempo de carga del detalle de proyecto paralelizando queries y agregando prefetch.",
    ]),
    ("Ene 2026", "Cofundador y desarrollador full-stack", "miFACU · remoto · ene 2026 – hoy", [
        "Plataforma publicada en Google Play y web: 642 de los 1.458 commits, junto a un socio.",
        "Diseñé la arquitectura de IA, con salidas estructuradas validadas por schema y reparación de JSON sin volver a llamar al modelo.",
        "Eliminé el throttling de analytics con un semáforo de concurrencia, backoff con jitter y caché en Redis.",
    ]),
    ("2024", "Soporte IT y asistencia técnica", "Freelance · Resistencia · 2024 – hoy", [
        "Diagnóstico y resolución de incidencias de hardware y software, presencial y remoto.",
        "Capacitación de usuarios sin formación técnica.",
    ]),
    ("2022", "Ingeniería en Sistemas de Información", "UTN · Facultad Regional Resistencia · 2022 – hoy", [
        "Tercer año en curso.",
    ]),
]

STACK = [
    ("Frontend", ["React 19", "Next.js 16", "React Native + Expo", "Tailwind CSS v4", "HeroUI", "TanStack Query"]),
    ("Backend y datos", ["Node.js", "Express", "PostgreSQL", "Supabase", "Redis", "TypeORM", "Zod", "Docker"]),
    ("IA y LLMs", ["Vercel AI SDK", "Gemini", "Claude", "DeepSeek", "OpenAI", "RAG", "Salidas estructuradas"]),
    ("Tiempo real y gráficos", ["Three.js", "Rapier", "Canvas 2D", "socket.io", "Supabase Realtime"]),
    ("Herramientas", ["Git y GitHub", "Vercel", "Railway", "PostHog", "RevenueCat", "Playwright"]),
]

SECCIONES = {
    "proyectos": ("01", "Proyectos", "Productos en producción, proyectos open source y experimentos. Los números salen de cada repositorio."),
    "experiencia": ("02", "Experiencia", "Dónde trabajé, qué construí y con quién."),
    "stack": ("03", "Stack", "Las herramientas que uso todos los días."),
    "actividad": ("04", "Actividad", "Mis contribuciones del último año."),
    "contacto": ("05", "Contacto", f"¿Tenés un proyecto o una búsqueda abierta? Escribime y te respondo. {PERFIL['disponibilidad']}."),
}

# ─── Tema ───────────────────────────────────────────────────────────────────

TEMAS = {
    "dark": {"bg": "#000000", "fg": "#ededed", "muted": "#8a8a8a", "border": "#1f1f1f",
             "borde_boton": "#2e2e2e", "punto": 0.09},
    "light": {"bg": "#ffffff", "fg": "#0a0a0a", "muted": "#6b6b6b", "border": "#e5e5e5",
              "borde_boton": "#d4d4d4", "punto": 0.12},
}

# Íconos de Tabler (los mismos que usa el portafolio), en una grilla de 24.
ICONOS = {
    "flecha": ["M17 7l-10 10", "M8 7l9 0l0 9"],
    "linkedin": ["M8 11v5", "M8 8v.01", "M12 16v-5", "M16 16v-3a2 2 0 1 0 -4 0",
                 "M3 7a4 4 0 0 1 4 -4h10a4 4 0 0 1 4 4v10a4 4 0 0 1 -4 4h-10a4 4 0 0 1 -4 -4l0 -10"],
    "cv": ["M14 3v4a1 1 0 0 0 1 1h4", "M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2",
           "M12 17v-6", "M9.5 14.5l2.5 2.5l2.5 -2.5"],
    "mail": ["M3 7a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-10", "M3 7l9 6l9 -6"],
    "web": ["M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0", "M3.6 9h16.8", "M3.6 15h16.8",
            "M11.5 3a17 17 0 0 0 0 18", "M12.5 3a17 17 0 0 1 0 18"],
}

# Signos del efecto de decodificación (los mismos que TextoDecodificado).
SIGNOS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*+=/<>_"

ANIMACIONES = """
.sube{animation:sube .55s cubic-bezier(.22,1,.36,1) backwards}
@keyframes sube{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.aparece{animation:aparece .7s cubic-bezier(.22,1,.36,1) backwards}
@keyframes aparece{from{opacity:0}}
.linea{animation:linea 1.1s cubic-bezier(.22,1,.36,1) backwards;transform-box:fill-box;transform-origin:left}
@keyframes linea{from{transform:scaleX(0)}}
.baja{animation:baja 2.4s cubic-bezier(.22,1,.36,1) backwards;transform-box:fill-box;transform-origin:top}
@keyframes baja{from{transform:scaleY(0)}}
.cursor{animation:cursor 1.1s steps(1,end) infinite}
@keyframes cursor{50%{opacity:0}}
.ping{animation:ping 1s cubic-bezier(0,0,.2,1) infinite;transform-box:fill-box;transform-origin:center}
@keyframes ping{75%,100%{transform:scale(2.6);opacity:0}}
.titila{opacity:0;animation:titila 5s ease-in-out infinite}
@keyframes titila{0%,100%{opacity:0}50%{opacity:.85}}
.forma{opacity:0;animation:forma 8s steps(1,end) infinite}
@keyframes forma{0%{opacity:1}6%,100%{opacity:0}}
.base{animation:base 8s steps(1,end) infinite}
@keyframes base{0%{opacity:0}6%,100%{opacity:1}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.titila,.forma{opacity:0}}
"""

# ─── Fuentes ────────────────────────────────────────────────────────────────


class Fuente:
    """Una instancia estática de una fuente variable, lista para medir y recortar."""

    def __init__(self, archivo: str, ejes: dict, familia: str):
        variable = TTFont(FUENTES / archivo)
        self.font = instancer.instantiateVariableFont(variable, ejes)
        self.font.flavor = None
        self.familia = familia
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font["hmtx"]
        self.upm = self.font["head"].unitsPerEm

    def avance(self, c: str, tam: float) -> float:
        glifo = self.cmap.get(ord(c), self.cmap[32])
        return self.hmtx[glifo][0] * tam / self.upm

    def ancho(self, texto: str, tam: float) -> float:
        return sum(self.avance(c, tam) for c in texto)

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


MONO = Fuente("GeistMono-latin.woff2", {"wght": 400}, "GM")
PIXEL = Fuente("GeistPixel-latin.woff2", {"ELSH": 0}, "GP")
# Otras formas del píxel (eje ELSH): las letras del nombre las alternan de a ratos.
FORMAS = [Fuente("GeistPixel-latin.woff2", {"ELSH": e}, f"GP{e}") for e in (50, 100)]

# ─── Lienzo SVG ─────────────────────────────────────────────────────────────


def esc(texto: str) -> str:
    return html.escape(texto, quote=True)


class Lienzo:
    def __init__(self, ancho: int, tema: str, titulo: str):
        self.ancho = ancho
        self.t = TEMAS[tema]
        self.titulo = titulo
        self.defs: list[str] = []
        self.partes: list[str] = []
        self.usado: dict[Fuente, set[str]] = {}

    def _usa(self, fuente: Fuente, texto: str):
        self.usado.setdefault(fuente, set()).update(texto)

    def color(self, nombre: str) -> str:
        return self.t.get(nombre, nombre)

    def texto(self, x, y, texto, tam, fuente=MONO, color="fg", ancla="start", opacidad=None,
              clase=None, estilo=None, extra=""):
        self._usa(fuente, texto)
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f"font-family=\"'{fuente.familia}',ui-monospace,monospace\"",
                 f'font-size="{tam}"', f'fill="{self.color(color)}"']
        if ancla != "start":
            attrs.append(f'text-anchor="{ancla}"')
        if opacidad is not None:
            attrs.append(f'fill-opacity="{opacidad}"')
        if clase:
            attrs.append(f'class="{clase}"')
        if estilo:
            attrs.append(f'style="{estilo}"')
        self.partes.append(f'<text {" ".join(attrs)} {extra}>{esc(texto)}</text>')

    def rect(self, x, y, w, h, color="border", extra=""):
        self.partes.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{self.color(color)}" {extra}/>')

    def icono(self, nombre, x, y, tam, color="fg", extra=""):
        escala = tam / 24
        trazos = "".join(f'<path d="{d}"/>' for d in ICONOS[nombre])
        self.partes.append(
            f'<g transform="translate({x:.1f} {y:.1f}) scale({escala:.4f})" fill="none" stroke="{self.color(color)}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" {extra}>{trazos}</g>'
        )

    def crudo(self, svg: str):
        self.partes.append(svg)

    def svg(self, alto: float, fondo=True, borde=True) -> str:
        css = "".join(f.css("".join(sorted(chars))) for f, chars in self.usado.items())
        cuerpo = []
        if fondo:
            cuerpo.append(f'<rect width="100%" height="100%" fill="{self.t["bg"]}"/>')
        cuerpo += self.partes
        if borde:
            cuerpo.append(f'<rect x=".5" y=".5" width="{self.ancho - 1}" height="{alto - 1:.1f}" fill="none" stroke="{self.t["border"]}"/>')
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.ancho}" height="{alto:.0f}" '
            f'viewBox="0 0 {self.ancho} {alto:.0f}" role="img" aria-label="{esc(self.titulo)}">'
            f"<title>{esc(self.titulo)}</title>"
            f"<style>{css}{ANIMACIONES}</style>"
            f'<defs>{"".join(self.defs)}</defs>'
            f'{"".join(cuerpo)}</svg>'
        )


def envolver(texto: str, max_ancho: float, medir) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if actual and medir(prueba) > max_ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    if actual:
        lineas.append(actual)
    return lineas


def campo_pixeles(lz: Lienzo, w, h, centro, radio, semilla, opacidad=1.0, encendidos=34):
    """Grilla de píxeles que se desvanece hacia los bordes, con algunos puntos que titilan."""
    t = lz.t
    lz.defs.append(
        f'<pattern id="grilla" width="22" height="22" patternUnits="userSpaceOnUse">'
        f'<rect x="10.25" y="10.25" width="1.5" height="1.5" fill="{t["fg"]}" fill-opacity="{t["punto"]}"/></pattern>'
        f'<radialGradient id="desvanecer" cx="{centro[0]}" cy="{centro[1]}" r="{radio}">'
        f'<stop offset=".1" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>'
        f'<mask id="mascara"><rect width="{w}" height="{h}" fill="url(#desvanecer)"/></mask>'
    )
    rnd = random.Random(semilla)
    puntos = []
    cx, cy = centro[0] * w, centro[1] * h
    while len(puntos) < encendidos:
        c, f = rnd.randrange(0, w // 22), rnd.randrange(0, h // 22)
        x, y = c * 22 + 11, f * 22 + 11
        # Más chances cerca del centro, donde la grilla se ve.
        if ((x - cx) / w) ** 2 + ((y - cy) / h) ** 2 > rnd.random() * radio ** 2:
            continue
        lado = rnd.choice([2.5, 3, 3.5, 4])
        puntos.append(
            f'<rect class="titila" x="{x - lado / 2}" y="{y - lado / 2}" width="{lado}" height="{lado}" fill="{t["fg"]}" '
            f'style="animation-delay:{rnd.uniform(0, 6):.2f}s;animation-duration:{rnd.uniform(3.5, 7):.2f}s"/>'
        )
    lz.crudo(
        f'<g mask="url(#mascara)" opacity="{opacidad}" shape-rendering="crispEdges">'
        f'<rect width="{w}" height="{h}" fill="url(#grilla)"/>{"".join(puntos)}</g>'
    )


# ─── Piezas ─────────────────────────────────────────────────────────────────

W = 840


def hero(tema: str) -> str:
    lz = Lienzo(W, tema, f"{' '.join(PERFIL['nombre'])} — desarrollador {', '.join(PERFIL['roles'])}")
    t = lz.t
    pad = 44
    alto = 600
    campo_pixeles(lz, W, alto, (0.72, 0.38), 0.62, semilla=7)

    # Ubicación, con el punto que late.
    chip_w = 12 + 6 + 10 + MONO.ancho(PERFIL["ubicacion"], 12) + 12
    lz.crudo(f'<g class="sube" style="animation-delay:.05s">')
    lz.rect(pad, 44, chip_w, 28, "bg", f'stroke="{t["border"]}"')
    lz.rect(pad + 12, 55, 6, 6, "fg", 'class="ping" opacity=".6"')
    lz.rect(pad + 12, 55, 6, 6, "fg")
    lz.texto(pad + 28, 62.5, PERFIL["ubicacion"], 12, color="muted")
    lz.crudo("</g>")

    # Nombre en Geist Pixel, letra por letra; algunas letras cambian de forma de a ratos.
    tam = 96
    rnd = random.Random(3)
    indice = 0
    y = 72 + 44 + tam * 0.74
    for linea in PERFIL["nombre"]:
        x = pad - 4
        for letra in linea:
            retraso = 0.15 + indice * 0.04
            lz.crudo(f'<g class="sube" style="animation-delay:{retraso:.2f}s">')
            if rnd.random() < 0.45:
                forma = rnd.choice(FORMAS)
                demora = rnd.uniform(2.5, 10)
                lz.texto(x, y, letra, tam, PIXEL, clase="base", estilo=f"animation-delay:{demora:.2f}s")
                lz.texto(x, y, letra, tam, forma, clase="forma", estilo=f"animation-delay:{demora:.2f}s")
            else:
                lz.texto(x, y, letra, tam, PIXEL)
            lz.crudo("</g>")
            x += PIXEL.avance(letra, tam)
            indice += 1
        y += tam * 0.95

    # "> desarrollador <rol>█", con el rol decodificándose como en el sitio.
    y_prompt = y - tam * 0.95 + 64
    tp = 22
    cw = MONO.avance("a", tp)
    lz.crudo('<g class="sube" style="animation-delay:.6s">')
    lz.texto(pad, y_prompt, ">", tp)
    lz.texto(pad + cw * 2, y_prompt, "desarrollador", tp, color="muted")
    x_rol = pad + cw * 16
    roles = PERFIL["roles"]
    intervalo, duracion, cuadros = 2.8, 0.7, 7
    total = intervalo * len(roles)
    rnd = random.Random(11)
    tramos = []  # (texto, inicio, fin)
    for k, rol in enumerate(roles):
        t0 = k * intervalo
        for j in range(cuadros):
            resueltos = int(j / cuadros * len(rol))
            ruido = "".join(" " if c == " " else rnd.choice(SIGNOS) for c in rol[resueltos:])
            tramos.append((rol[:resueltos] + ruido, t0 + j * duracion / cuadros, t0 + (j + 1) * duracion / cuadros))
        tramos.append((rol, t0 + duracion, t0 + intervalo))
    for texto, a, b in tramos:
        if a == 0:
            valores, tiempos = "1;0", f"0;{b / total:.4f}"
        else:
            valores, tiempos = "0;1;0", f"0;{a / total:.4f};{b / total:.4f}"
        lz.texto(x_rol, y_prompt, texto, tp, opacidad=None, estilo="white-space:pre",
                 extra=f'opacity="0"><animate attributeName="opacity" values="{valores}" keyTimes="{tiempos}" '
                       f'calcMode="discrete" dur="{total}s" repeatCount="indefinite"/')
    # Cursor: salta al final de cada rol.
    xs, ts = [], []
    for k, rol in enumerate(roles):
        xs.append(f"{x_rol + cw * len(rol) + 3:.1f}")
        ts.append(f"{k * intervalo / total:.4f}")
    lz.crudo(
        f'<rect class="cursor" x="{xs[0]}" y="{y_prompt - tp * 0.8:.1f}" width="{cw:.1f}" height="{tp * 0.95:.1f}" fill="{t["fg"]}">'
        f'<animate attributeName="x" values="{";".join(xs)}" keyTimes="{";".join(ts)}" '
        f'calcMode="discrete" dur="{total}s" repeatCount="indefinite"/></rect>'
    )
    lz.crudo("</g>")

    # Resumen.
    y_res = y_prompt + 46
    lineas = envolver(PERFIL["resumen"], 640, lambda s: MONO.ancho(s, 14))
    lz.crudo('<g class="sube" style="animation-delay:.75s">')
    for i, linea in enumerate(lineas):
        lz.texto(pad, y_res + i * 24, linea, 14, color="muted")
    lz.crudo("</g>")

    # Cifras.
    y_cif = y_res + (len(lineas) - 1) * 24 + 40
    lz.rect(pad, y_cif, W - 2 * pad, 1, "border", 'class="linea" style="animation-delay:.9s"')
    col = (W - 2 * pad) / 4
    filas = 1
    for i, (valor, etiqueta) in enumerate(CIFRAS):
        lz.crudo(f'<g class="sube" style="animation-delay:{1 + i * 0.08:.2f}s">')
        lz.texto(pad + i * col, y_cif + 52, valor, 38, PIXEL)
        lineas_et = envolver(etiqueta, col - 20, lambda s: MONO.ancho(s, 12))
        filas = max(filas, len(lineas_et))
        for j, linea in enumerate(lineas_et):
            lz.texto(pad + i * col, y_cif + 76 + j * 17, linea, 12, color="muted")
        lz.crudo("</g>")
    return lz.svg(y_cif + 108 + (filas - 1) * 17)


def seccion(clave: str, tema: str) -> str:
    numero, titulo, bajada = SECCIONES[clave]
    lz = Lienzo(W, tema, f"{numero} — {titulo}")
    derecha = f"/ {titulo.lower()}"
    x_linea = MONO.ancho(numero, 12) + 16
    fin_linea = W - MONO.ancho(derecha, 12) - 16
    aire = 48  # separación con lo que hay arriba
    lz.crudo(f'<g transform="translate(0 {aire})">')
    lz.texto(0, 20, numero, 12)
    lz.rect(x_linea, 15.5, fin_linea - x_linea, 1, "border", 'class="linea"')
    lz.texto(W, 20, derecha, 12, color="muted", ancla="end")
    x = 0
    for i, letra in enumerate(titulo):
        lz.crudo(f'<g class="sube" style="animation-delay:{0.1 + i * 0.04:.2f}s">')
        lz.texto(x, 104, letra, 60, PIXEL)
        lz.crudo("</g>")
        x += PIXEL.avance(letra, 60)
    lineas = envolver(bajada, W - 120, lambda s: MONO.ancho(s, 14))
    lz.crudo('<g class="sube" style="animation-delay:.3s">')
    for i, linea in enumerate(lineas):
        lz.texto(0, 146 + i * 24, linea, 14, color="muted")
    lz.crudo("</g></g>")
    return lz.svg(aire + 146 + (len(lineas) - 1) * 24 + 16, fondo=False, borde=False)


def chips(lz: Lienzo | None, x0, y0, ancho_max, items, tam, pad, alto, sep, color="muted", opacidad=None):
    """Etiquetas con borde, en filas. Devuelve el alto ocupado."""
    x, y = x0, y0
    for item in items:
        w = MONO.ancho(item, tam) + 2 * pad
        if x > x0 and x + w > x0 + ancho_max:
            x, y = x0, y + alto + sep
        if lz:
            lz.rect(x + 0.5, y + 0.5, w - 1, alto - 1, "none", f'stroke="{lz.t["border"]}"')
            lz.texto(x + pad, y + alto / 2 + tam * 0.36, item, tam, color=color, opacidad=opacidad)
        x += w + sep
    return y + alto - y0


CARD_W = 412
CARD_PAD = 28


def medir_tarjeta(p) -> tuple[float, float]:
    """Alto de la parte de arriba (texto) y de abajo (stack + pie) de una tarjeta."""
    interior = CARD_W - 2 * CARD_PAD
    arriba = 40 + 50
    arriba += 24 * len(envolver(p["bajada"], interior, lambda s: MONO.ancho(s, 13)))
    arriba += 12 + 20 * len(envolver(p["descripcion"], interior, lambda s: MONO.ancho(s, 12.5)))
    for d in p["destacados"]:
        arriba += 8 + 20 * len(envolver(d, interior - 22, lambda s: MONO.ancho(s, 12.5)))
    abajo = 20 + chips(None, 0, 0, interior, p["stack"], 11, 8, 22, 6) + 18 + 1 + 16 + pie_lineas(p) * 20
    return arriba, abajo


def pie(p) -> tuple[list[tuple[int, float, str]], int]:
    """Ubica rol y enlaces como el flex-wrap del sitio: todo en una fila si entra
    (rol a la izquierda, enlaces a la derecha); si no, los enlaces bajan alineados
    a la izquierda. Devuelve (fila, x, enlace) y la cantidad de filas."""
    interior = CARD_W - 2 * CARD_PAD
    anchos = [MONO.ancho(e, 12) + 2 + 14 for e in p["enlaces"]]
    total = sum(anchos) + 16 * (len(anchos) - 1)
    if MONO.ancho(p["rol"], 12) + 20 + total <= interior:
        x = interior - total
        pos = []
        for e, w in zip(p["enlaces"], anchos):
            pos.append((0, x, e))
            x += w + 16
        return pos, 1
    pos, fila, x = [], 1, 0.0
    for e, w in zip(p["enlaces"], anchos):
        if x > 0 and x + w > interior:
            fila, x = fila + 1, 0.0
        pos.append((fila, x, e))
        x += w + 16
    return pos, fila + 1


def pie_lineas(p) -> int:
    return pie(p)[1]


def tarjeta(p, indice: int, tema: str, alto_arriba: float, alto_abajo: float) -> str:
    lz = Lienzo(CARD_W, tema, f"{p['nombre']} — {p['bajada']}")
    interior = CARD_W - 2 * CARD_PAD
    x = CARD_PAD
    lz.texto(x, 40, f"{indice + 1:02d}", 12, color="muted")
    lz.texto(CARD_W - CARD_PAD, 40, p["periodo"], 12, color="muted", ancla="end")
    lz.texto(x, 90, p["nombre"], 36, PIXEL)
    y = 90
    for linea in envolver(p["bajada"], interior, lambda s: MONO.ancho(s, 13)):
        y += 24
        lz.texto(x, y, linea, 13, opacidad=0.8)
    y += 12
    for linea in envolver(p["descripcion"], interior, lambda s: MONO.ancho(s, 12.5)):
        y += 20
        lz.texto(x, y, linea, 12.5, color="muted")
    for d in p["destacados"]:
        y += 8
        for j, linea in enumerate(envolver(d, interior - 22, lambda s: MONO.ancho(s, 12.5))):
            y += 20
            if j == 0:
                lz.texto(x, y, "—", 12.5, color="muted")
            lz.texto(x + 22, y, linea, 12.5, opacidad=0.85)

    # Stack y pie, pegados abajo.
    y = alto_arriba + 20 + (alto_abajo - medir_tarjeta(p)[1])
    y += chips(lz, x, y, interior, p["stack"], 11, 8, 22, 6) + 18
    lz.rect(x, y, interior, 1, "border")
    y += 1 + 16 + 4
    lz.texto(x, y + 4, p["rol"], 12, color="muted")
    posiciones, _ = pie(p)
    for fila, xe, enlace in posiciones:
        yf = y + fila * 20
        lz.texto(x + xe, yf + 4, enlace, 12)
        lz.icono("flecha", x + xe + MONO.ancho(enlace, 12) + 2, yf - 7, 14)
    return lz.svg(alto_arriba + alto_abajo + CARD_PAD)


def experiencia(tema: str) -> str:
    lz = Lienzo(W, tema, "Experiencia: " + "; ".join(f"{e[1]} en {e[2]}" for e in EXPERIENCIA))
    t = lz.t
    x_cont = 300
    x_txt = x_cont + 28
    ancho_txt = W - x_txt - 32
    y = 56
    bloques = []
    for i, (periodo, puesto, lugar, puntos) in enumerate(EXPERIENCIA):
        y0 = y
        lz.crudo(f'<g class="sube" style="animation-delay:{0.1 + i * 0.1:.2f}s">')
        lz.rect(27, y - 22, 11, 11, "fg")
        lz.texto(72, y - 8, periodo, 28, PIXEL, color="muted")
        for linea in envolver(puesto, ancho_txt, lambda s: PIXEL.ancho(s, 26)):
            lz.texto(x_txt, y, linea, 26, PIXEL)
            y += 32
        y += 2
        lz.texto(x_txt, y, lugar, 12, color="muted")
        y += 12
        for punto in puntos:
            for j, linea in enumerate(envolver(punto, ancho_txt - 22, lambda s: MONO.ancho(s, 13))):
                y += 22
                if j == 0:
                    lz.texto(x_txt, y, "—", 13, color="muted")
                lz.texto(x_txt + 22, y, linea, 13, opacidad=0.8)
            y += 6
        lz.crudo("</g>")
        bloques.append((y0 - 30, y + 4))
        y += 56
    alto = y - 20
    for a, b in bloques:
        lz.rect(x_cont, a, 1, b - a, "border")
    # Línea de tiempo: borde que se desvanece en las puntas y un haz que baja.
    lz.defs.append(
        f'<linearGradient id="riel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["border"]}" stop-opacity="0"/>'
        f'<stop offset=".08" stop-color="{t["border"]}"/><stop offset=".92" stop-color="{t["border"]}"/>'
        f'<stop offset="1" stop-color="{t["border"]}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="haz" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{t["fg"]}"/>'
        f'<stop offset=".1" stop-color="{t["fg"]}" stop-opacity=".4"/><stop offset="1" stop-color="{t["fg"]}" stop-opacity="0"/></linearGradient>'
    )
    lz.partes.insert(0, f'<rect x="32" y="16" width="1" height="{alto - 32}" fill="url(#riel)"/>'
                        f'<rect class="baja" x="32" y="16" width="1" height="{alto - 32}" fill="url(#haz)"/>')
    return lz.svg(alto)


def stack(tema: str) -> str:
    lz = Lienzo(W, tema, "Stack: " + "; ".join(f"{g}: {', '.join(i)}" for g, i in STACK))
    x_chips = 260
    y = 0
    for i, (grupo, items) in enumerate(STACK):
        lz.crudo(f'<g class="sube" style="animation-delay:{i * 0.06:.2f}s">')
        alto_fila = chips(None, 0, 0, W - x_chips - 28, items, 12, 10, 28, 8)
        lz.texto(28, y + 26 + 18.5, f"{i + 1:02d}", 12)
        lz.texto(28 + MONO.ancho("00 ", 12), y + 26 + 18.5, grupo.lower(), 12, color="muted")
        chips(lz, x_chips, y + 26, W - x_chips - 28, items, 12, 10, 28, 8, color="fg", opacidad=0.85)
        lz.crudo("</g>")
        y += 26 + alto_fila + 26
        if i < len(STACK) - 1:
            lz.rect(0, y, W, 1, "border")
    return lz.svg(y)


def contacto(tema: str) -> str:
    lz = Lienzo(W, tema, f"Escribime a {PERFIL['email']}")
    alto = 150
    campo_pixeles(lz, W, alto, (0.8, 0.8), 0.6, semilla=21, opacidad=0.6, encendidos=14)
    x = 36
    for i, letra in enumerate(PERFIL["email"]):
        lz.crudo(f'<g class="sube" style="animation-delay:{0.1 + i * 0.03:.2f}s">')
        lz.texto(x, 96, letra, 52, PIXEL)
        lz.crudo("</g>")
        x += PIXEL.avance(letra, 52)
    lz.icono("flecha", x + 10, 56, 44, color="muted")
    return lz.svg(alto)


def boton(texto: str, icono: str | None, variante: str, tema: str) -> str:
    t = TEMAS[tema]
    tam, alto, pad = 14, 44, 20
    w_icono = 16 + 8 if icono else 0
    ancho = round(pad * 2 + w_icono + MONO.ancho(texto, tam))
    lz = Lienzo(ancho, tema, texto)
    if variante == "primario":
        lz.rect(0, 0, ancho, alto, "fg")
        color = t["bg"]
    else:
        lz.rect(0.5, 0.5, ancho - 1, alto - 1, "none", f'stroke="{t["borde_boton"]}"')
        color = t["fg"]
    x = pad
    if icono:
        lz.icono(icono, x, alto / 2 - 8, 16, color=color)
        x += w_icono
    lz.texto(x, alto / 2 + 5, texto, tam, color=color)
    return lz.svg(alto, fondo=False, borde=False)


# ─── README ─────────────────────────────────────────────────────────────────


def imagen(nombre: str, alt: str, ancho: str | None = None) -> str:
    w = f' width="{ancho}"' if ancho else ""
    return (
        f'<picture><source media="(prefers-color-scheme: dark)" srcset="./assets/{nombre}-dark.svg" />'
        f'<img src="./assets/{nombre}-light.svg" alt="{esc(alt)}"{w} /></picture>'
    )


def enlace(href: str, contenido: str) -> str:
    return f'<a href="{href}">{contenido}</a>'


SNAKE = "https://raw.githubusercontent.com/Facu-Basualdo/Facu-Basualdo/output/github-contribution-grid-snake"

BOTONES = [
    ("portafolio", "basualdo.dev", "web", "primario", PERFIL["web"]),
    ("cv", "Descargar CV", "cv", "contorno", PERFIL["cv"]),
    ("linkedin", "LinkedIn", "linkedin", "contorno", PERFIL["linkedin"]),
    ("email", "Email", "mail", "contorno", f"mailto:{PERFIL['email']}"),
]


def readme() -> str:
    r = []
    r.append(enlace(PERFIL["web"], imagen("hero", "Facundo Basualdo — desarrollador full-stack, de producto, de IA aplicada y de tiempo real. " + PERFIL["resumen"], "100%")))
    r.append("")
    r.append("<p>\n  " + "\n  ".join(enlace(href, imagen(f"boton-{clave}", texto, None)) for clave, texto, _, _, href in BOTONES) + "\n</p>")
    r.append("")
    r.append(imagen("seccion-proyectos", "01 — Proyectos", "100%"))
    r.append("")
    for i in range(0, len(PROYECTOS), 2):
        par = PROYECTOS[i:i + 2]
        r.append("<p>\n  " + "\n  ".join(
            enlace(p["destino"], imagen(f"proyecto-{p['id']}", f"{p['nombre']} — {p['bajada']}. {p['descripcion']}", "49%"))
            for p in par) + "\n</p>")
    r.append("")
    r.append(imagen("seccion-experiencia", "02 — Experiencia", "100%"))
    r.append("")
    r.append(imagen("experiencia", "Experiencia", "100%"))
    r.append("")
    r.append(imagen("seccion-stack", "03 — Stack", "100%"))
    r.append("")
    r.append(imagen("stack", "Stack", "100%"))
    r.append("")
    r.append(imagen("seccion-actividad", "04 — Actividad", "100%"))
    r.append("")
    r.append(
        f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{SNAKE}-dark.svg" />\n'
        f'  <img alt="Contribuciones en GitHub" src="{SNAKE}.svg" width="100%" />\n</picture>'
    )
    r.append("")
    r.append(imagen("seccion-contacto", "05 — Contacto", "100%"))
    r.append("")
    r.append(enlace(f"mailto:{PERFIL['email']}", imagen("contacto", f"Escribime a {PERFIL['email']}", "100%")))
    r.append("")
    r.append("<p>\n  " + "\n  ".join(enlace(href, imagen(f"boton-{clave}", texto, None)) for clave, texto, _, _, href in BOTONES[1:]) + "\n</p>")
    r.append("")
    r.append("<!-- Generado con scripts/generar.py: editá los datos ahí y volvé a correrlo. -->")
    return "\n".join(r) + "\n"


def main():
    ASSETS.mkdir(exist_ok=True)
    for viejo in ASSETS.glob("*"):
        viejo.unlink()
    archivos = {}
    for tema in TEMAS:
        archivos[f"hero-{tema}"] = hero(tema)
        for clave in SECCIONES:
            archivos[f"seccion-{clave}-{tema}"] = seccion(clave, tema)
        for i in range(0, len(PROYECTOS), 2):
            par = PROYECTOS[i:i + 2]
            medidas = [medir_tarjeta(p) for p in par]
            arriba = max(m[0] for m in medidas)
            abajo = max(m[1] for m in medidas)
            for j, p in enumerate(par):
                archivos[f"proyecto-{p['id']}-{tema}"] = tarjeta(p, i + j, tema, arriba, abajo)
        archivos[f"experiencia-{tema}"] = experiencia(tema)
        archivos[f"stack-{tema}"] = stack(tema)
        archivos[f"contacto-{tema}"] = contacto(tema)
        for clave, texto, icono, variante, _ in BOTONES:
            archivos[f"boton-{clave}-{tema}"] = boton(texto, icono, variante, tema)
    for nombre, contenido in archivos.items():
        (ASSETS / f"{nombre}.svg").write_text(contenido, encoding="utf-8")
    (RAIZ / "README.md").write_text(readme(), encoding="utf-8")
    total = sum(len(c.encode()) for c in archivos.values())
    print(f"{len(archivos)} SVG ({total / 1024:.0f} KB) y README.md generados.")


if __name__ == "__main__":
    main()
