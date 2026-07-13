# Mega-Prompt — One Prompt Wonder

Plantilla para replicar un producto con UN solo prompt en Codex.
El día del evento: rellená los 3 placeholders `{{...}}` y pegá. Nada más.

> **Tip:** si te dan screenshot, adjuntalo y dejá que la Fase 1 haga el trabajo.
> Si te dan código, pegalo donde dice `{{SPEC_VISUAL}}`.

---

## LA PLANTILLA (copiar desde acá)

```
Actuá como un equipo de producto completo trabajando en secuencia: analista de UI,
diseñador de sistemas de diseño, frontend senior y QA. Ejecutá las 4 fases en orden,
en una sola respuesta, sin hacerme NINGUNA pregunta. Ante cualquier ambigüedad,
asumí la convención más común para este tipo de producto.

PRODUCTO A REPLICAR: {{DESCRIPCION}}
(ej: "Tienda virtual de zapatillas, ver screenshot adjunto")

REFERENCIA: {{SPEC_VISUAL}}
(screenshot adjunto / código pegado / descripción detallada)

ARQUETIPO Y COMPONENTES OBLIGATORIOS:
{{ARQUETIPO}}
(pegar acá el bloque del arquetipo correspondiente de 2-arquetipos.md)

═══ FASE 1 — SPEC (interna, no la muestres) ═══
Extraé de la referencia: layout y grilla, paleta exacta de colores (hex), tipografía,
espaciados, todos los componentes visibles con sus estados, textos y datos visibles,
y si es tema claro u oscuro. Si algo no se ve, inferilo del arquetipo.

═══ FASE 2 — DISEÑO ═══
Definí design tokens (CSS custom properties) con la paleta, tipografía y espaciados
del spec. Usá una escala de espaciado consistente (4/8px).

═══ FASE 3 — IMPLEMENTACIÓN ═══
Entregá UN SOLO archivo HTML autocontenido:
- CSS y JS inline (en <style> y <script>), sin build, sin frameworks.
- Solo se permite CDN si es imprescindible (íconos, fuentes de Google Fonts).
- Imágenes: https://picsum.photos/seed/{nombre}/{w}/{h} o SVG inline. NUNCA rutas locales.
- Datos: generá 8-12 registros realistas y variados (nombres, precios, fechas creíbles,
  en el idioma que muestra la referencia). Nada de "Item 1, Item 2".
- Funcional de verdad: botones, filtros, tabs, modales, carrito/contador — todo lo que
  se ve en la referencia debe responder al click con JS real (estado en memoria).
- Estados: hover, active, focus visible, y al menos un empty state.
- Responsive: desktop primero (así se ve la referencia), colapsando a mobile con
  menú hamburguesa si aplica.
- Accesible: HTML semántico, alt en imágenes, contraste suficiente.

═══ FASE 4 — QA (antes de responder) ═══
Compará tu implementación contra el spec de la Fase 1, ítem por ítem. Verificá que:
todos los componentes de la referencia existen, los colores coinciden, no hay JS con
errores, no quedó ningún TODO ni placeholder vacío. Corregí lo que falle y recién
entonces entregá el archivo final completo.

FORMATO DE RESPUESTA: únicamente el archivo HTML completo, sin explicaciones antes
ni después.
```

---

## Por qué funciona

- **Fases = tus "varios agentes"**, pero dentro de un prompt. El modelo planifica antes de codear y se auto-revisa antes de entregar.
- **"Sin preguntas + asumí la convención"** elimina el riesgo de que te devuelva una pregunta y quemes tu único turno.
- **Contrato de salida rígido** (1 HTML, picsum, datos realistas, todo clickeable) evita los fallos típicos: imágenes rotas, botones muertos, lorem ipsum.
- **QA al final** recupera detalles que el modelo suele dejar caer en respuestas largas.

## Variantes rápidas

- **Poco tiempo / producto simple:** borrá Fase 2 y fusionala con la 3.
- **Te dan código en vez de screenshot:** en Fase 1 cambiá "extraé de la referencia" por "leé el código y extraé el spec funcional y visual; mejorá el diseño donde sea genérico".
- **En inglés:** si notás que Codex rinde mejor en inglés, traducí la plantilla — la estructura es lo que importa. Practicá con ambas y quedate con la que mida mejor en tu kit de práctica.
