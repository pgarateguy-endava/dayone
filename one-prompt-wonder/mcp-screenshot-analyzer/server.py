"""
MCP Screenshot Analyzer — convierte un screenshot en un spec listo para el mega-prompt.

Tools:
  - analizar_screenshot(path): paleta de colores, dimensiones, tema claro/oscuro,
    zonas de layout detectadas por heurística.
  - extraer_texto(path): OCR con pytesseract (opcional, requiere tesseract instalado).
  - generar_spec(path): combina ambos y devuelve un bloque de texto listo para pegar
    en el placeholder {{SPEC_VISUAL}} del mega-prompt.

Uso con Codex CLI (~/.codex/config.toml):

  [mcp_servers.screenshot-analyzer]
  command = "python3"
  args = ["/ruta/absoluta/a/server.py"]

También sirve standalone (sin MCP):  python3 server.py --spec captura.png
"""

import sys
from collections import Counter
from pathlib import Path

from PIL import Image

try:
    from mcp.server.fastmcp import FastMCP
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


# ---------- Núcleo de análisis (independiente de MCP) ----------

def _hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb[:3])


def paleta(path: str, n: int = 8) -> list[dict]:
    """Colores dominantes con % de cobertura."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((400, 400))
    q = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT).convert("RGB")
    counts = Counter(q.getdata())
    total = sum(counts.values())
    return [
        {"hex": _hex(c), "porcentaje": round(100 * k / total, 1)}
        for c, k in counts.most_common(n)
    ]


def tema(colores: list[dict]) -> str:
    """Claro u oscuro según luminosidad del color dominante."""
    r, g, b = (int(colores[0]["hex"][i:i + 2], 16) for i in (1, 3, 5))
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return "oscuro" if lum < 128 else "claro"


def zonas_layout(path: str) -> dict:
    """Heurística: compara franjas de la imagen para detectar navbar/sidebar/footer."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((200, 200))
    w, h = img.size

    def color_medio(box):
        region = img.crop(box).resize((1, 1))
        return region.getpixel((0, 0))

    def distinto(c1, c2, umbral=40):
        return sum(abs(a - b) for a, b in zip(c1, c2)) > umbral

    centro = color_medio((w // 4, h // 4, 3 * w // 4, 3 * h // 4))
    top = color_medio((0, 0, w, max(1, h // 12)))
    bottom = color_medio((0, h - max(1, h // 12), w, h))
    left = color_medio((0, 0, max(1, w // 6), h))

    return {
        "navbar_probable": distinto(top, centro),
        "footer_probable": distinto(bottom, centro),
        "sidebar_probable": distinto(left, centro),
        "aspecto": "desktop" if w / h > 1.2 else "mobile" if w / h < 0.8 else "cuadrado",
    }


def ocr(path: str) -> str:
    try:
        import pytesseract
        texto = pytesseract.image_to_string(Image.open(path), lang="spa+eng")
        return texto.strip() or "(no se detectó texto)"
    except Exception as e:
        return f"(OCR no disponible: {e}. Instalar: pip install pytesseract && brew install tesseract)"


def spec(path: str) -> str:
    """Bloque listo para pegar en {{SPEC_VISUAL}}."""
    p = Path(path)
    if not p.exists():
        return f"ERROR: no existe {path}"
    img = Image.open(path)
    cols = paleta(path)
    z = zonas_layout(path)
    texto = ocr(path)
    lineas_texto = "\n".join(f"  {l}" for l in texto.splitlines()[:40] if l.strip())
    paleta_str = ", ".join(f"{c['hex']} ({c['porcentaje']}%)" for c in cols)
    return f"""SPEC EXTRAÍDO DEL SCREENSHOT ({p.name}, {img.size[0]}x{img.size[1]}px):
- Tema: {tema(cols)}
- Paleta dominante: {paleta_str}
- Layout detectado: navbar={z['navbar_probable']}, sidebar={z['sidebar_probable']}, footer={z['footer_probable']}, formato={z['aspecto']}
- Texto visible (OCR):
{lineas_texto}"""


# ---------- Capa MCP ----------

if HAS_MCP:
    mcp = FastMCP("screenshot-analyzer")

    @mcp.tool()
    def analizar_screenshot(path: str) -> dict:
        """Analiza un screenshot: paleta de colores hex, tema claro/oscuro y layout."""
        cols = paleta(path)
        return {"paleta": cols, "tema": tema(cols), "layout": zonas_layout(path)}

    @mcp.tool()
    def extraer_texto(path: str) -> str:
        """Extrae el texto visible del screenshot vía OCR."""
        return ocr(path)

    @mcp.tool()
    def generar_spec(path: str) -> str:
        """Genera un spec completo listo para pegar en el mega-prompt ({{SPEC_VISUAL}})."""
        return spec(path)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--spec":
        print(spec(sys.argv[2]))
    elif HAS_MCP:
        mcp.run()
    else:
        print("Uso standalone: python3 server.py --spec captura.png")
        print("Para modo MCP: pip install mcp pillow")
        sys.exit(1)
