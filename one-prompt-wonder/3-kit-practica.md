# Kit de práctica — One Prompt Wonder

Objetivo: llegar al evento con el mega-prompt ya calibrado. **5 corridas cronometradas** en Codex, una por día si podés.

## Reglas de cada corrida

1. Elegí un screenshot de referencia (abajo hay dónde conseguirlos).
2. Cronómetro: **máx. 10 min** para armar el prompt (identificar arquetipo + rellenar plantilla).
3. Pegás el prompt en Codex. **Un solo envío. Sin follow-ups.** Lo que sale, sale.
4. Abrís el HTML en el navegador y evaluás con la rúbrica.
5. Anotás en el log qué falló y ajustás la plantilla o el arquetipo — no el resultado.

## Los 5 ejercicios

| # | Producto | Referencia sugerida | Dificultad |
|---|----------|--------------------|------------|
| 1 | Tienda virtual | Home de una tienda Shopify cualquiera | ⭐⭐ |
| 2 | Dashboard admin | Screenshot de demo de Tailwind UI / Vercel dashboard | ⭐⭐⭐ |
| 3 | Landing SaaS | linear.app o stripe.com | ⭐⭐ |
| 4 | Kanban | Board de Trello con tarjetas | ⭐⭐⭐⭐ (drag & drop) |
| 5 | Sorpresa | Pedile a un colega que elija — simula el evento | ⭐⭐⭐⭐ |

Screenshots: sacalos vos mismo de sitios reales (Cmd+Shift+4), o de dribbble.com buscando "e-commerce ui", "admin dashboard", etc.

## Rúbrica (puntuá cada corrida sobre 100)

| Criterio | Pts | Qué mirar |
|----------|-----|-----------|
| Fidelidad visual | 40 | Paleta, layout, tipografía, espaciados vs. la referencia. ¿Un tercero diría "es el mismo producto"? |
| Funcionalidad | 30 | Todo lo clickeable funciona: carrito suma, filtros filtran, modales abren, sin errores en consola (F12). |
| Datos y pulido | 20 | Datos realistas (no "Item 1"), imágenes que cargan, hover states, empty states. |
| Robustez | 10 | Responsive sin romperse, sin placeholders/TODOs, funciona al primer intento. |

**Meta: promedio ≥ 75 antes del evento.** Si un criterio falla 2 veces seguidas, el fix va a la plantilla (ej: si los filtros nunca funcionan, reforzá esa línea en Fase 3).

## Log de iteración (copiá por corrida)

```
Corrida #_ — Fecha: ____ — Producto: ____
Puntaje: Visual _/40 | Funcional _/30 | Datos _/20 | Robustez _/10 = _/100
Qué falló:
Qué cambié en la plantilla:
```

## Checklist del día del evento

- [ ] Mega-prompt abierto en una pestaña, arquetipos en otra.
- [ ] Identificar arquetipo → copiar bloque → rellenar 3 placeholders. Nada improvisado.
- [ ] Releer 10 segundos antes de enviar: ¿quedó algún `{{...}}` sin rellenar?
- [ ] Si dan código en vez de captura: usar la variante "código" de 1-mega-prompt.md.
- [ ] Respirar. Un solo envío.
