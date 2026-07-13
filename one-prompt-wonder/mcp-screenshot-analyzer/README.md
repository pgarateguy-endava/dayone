# MCP Screenshot Analyzer

Convierte un screenshot en un spec (paleta hex, tema, layout, texto OCR) listo para pegar en el `{{SPEC_VISUAL}}` del mega-prompt.

## Instalación

```bash
pip install mcp pillow
# OCR opcional pero recomendado:
pip install pytesseract
brew install tesseract tesseract-lang   # macOS
```

## Opción A — Como MCP en Codex CLI

Agregar a `~/.codex/config.toml`:

```toml
[mcp_servers.screenshot-analyzer]
command = "python3"
args = ["/ruta/absoluta/a/server.py"]
```

Reiniciar Codex. Después, en tu prompt podés decirle: *"usá la tool generar_spec con la captura X antes de la Fase 1"*.

## Opción B — Standalone (si el evento es en Codex web o no permite MCP)

Corrélo ANTES en tu terminal y pegá la salida en el mega-prompt:

```bash
python3 server.py --spec captura.png
```

Salida de ejemplo:

```
SPEC EXTRAÍDO DEL SCREENSHOT (captura.png, 1440x900px):
- Tema: claro
- Paleta dominante: #ffffff (42.1%), #1a73e8 (18.3%), ...
- Layout detectado: navbar=True, sidebar=False, footer=True, formato=desktop
- Texto visible (OCR): ...
```

⚠️ **Confirmá las reglas del evento**: si "un solo prompt" prohíbe pre-procesar la captura con tus herramientas, usá el mega-prompt solo — la Fase 1 hace este análisis dentro del propio prompt.

## Tools expuestas (modo MCP)

- `analizar_screenshot(path)` — paleta, tema, layout
- `extraer_texto(path)` — OCR
- `generar_spec(path)` — todo junto, formateado para el mega-prompt
