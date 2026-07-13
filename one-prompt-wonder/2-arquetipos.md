# Arquetipos — componentes obligatorios por tipo de producto

El día del evento: identificá el arquetipo, copiá su bloque y pegalo en `{{ARQUETIPO}}` del mega-prompt. Si el producto mezcla dos, pegá ambos.

---

## 🛒 Tienda virtual / e-commerce

```
Tipo: TIENDA VIRTUAL. Componentes obligatorios:
- Navbar: logo, buscador, links de categorías, ícono de carrito con contador (badge).
- Hero o banner promocional con CTA.
- Sidebar o barra de filtros: categoría, rango de precio, ordenamiento (funcionales).
- Grid de productos (mín. 8): imagen, nombre, precio, precio tachado si hay descuento,
  rating con estrellas, botón "Agregar al carrito" que actualiza el contador.
- Badge de "Oferta"/"Nuevo" en algunos productos.
- Drawer o modal de carrito: lista de items, cantidades editables, total calculado.
- Footer con columnas de links.
Interacciones: agregar/quitar del carrito, filtrar y ordenar en vivo, búsqueda que filtra.
```

## 📊 Dashboard admin / analytics

```
Tipo: DASHBOARD ADMIN. Componentes obligatorios:
- Sidebar de navegación colapsable con íconos y sección activa resaltada.
- Topbar: buscador, notificaciones con badge, avatar con menú.
- Fila de 4 KPI cards: valor grande, label, delta % con flecha verde/roja.
- 2 gráficos como SVG inline dibujados a mano (línea y barras) con datos coherentes
  con los KPIs. Nada de librerías de charts salvo que la referencia lo exija.
- Tabla de datos: encabezados ordenables, estados con pills de color, paginación,
  checkbox por fila.
Interacciones: ordenar tabla, colapsar sidebar, tabs de rango temporal que cambian los datos.
```

## 🚀 Landing SaaS

```
Tipo: LANDING SAAS. Componentes obligatorios:
- Navbar sticky: logo, links, CTA destacado.
- Hero: headline potente, subheadline, 2 CTAs, mockup del producto (hecho en CSS/SVG).
- Logos de "confían en nosotros" (texto o SVG).
- Grid de 3-6 features con ícono, título, descripción.
- Sección de pricing: 3 planes, el del medio destacado, toggle mensual/anual funcional.
- Testimonios con avatar (picsum), nombre y cargo.
- FAQ con acordeón funcional.
- Footer completo.
Interacciones: toggle de pricing recalcula precios, acordeón abre/cierra, scroll suave a anclas.
```

## 📋 Kanban / gestión de proyectos

```
Tipo: KANBAN. Componentes obligatorios:
- Topbar: nombre del board, avatares del equipo apilados, botón "+ Nueva tarea".
- 3-4 columnas (Backlog / En curso / Review / Hecho) con contador de tarjetas.
- Tarjetas: título, etiquetas de color, avatar asignado, fecha, ícono de comentarios.
- Drag & drop real entre columnas (HTML5 drag events).
- Modal de detalle al clickear tarjeta y modal de creación funcional.
Interacciones: crear tarea, arrastrar entre columnas, filtrar por etiqueta.
```

## 💬 Chat / mensajería

```
Tipo: CHAT. Componentes obligatorios:
- Sidebar de conversaciones: avatar, nombre, preview del último mensaje, hora,
  badge de no leídos, conversación activa resaltada.
- Header del chat: avatar, nombre, estado en línea.
- Hilo de mensajes: burbujas propias a la derecha / ajenas a la izquierda, timestamps,
  separadores de fecha, avatar en mensajes ajenos.
- Input con botón enviar (Enter también envía) que agrega el mensaje al hilo.
- Respuesta automática simulada a los 1-2 segundos para que se vea vivo.
Interacciones: cambiar de conversación carga otro hilo, enviar mensaje, indicador "escribiendo...".
```

## 📱 Feed / red social

```
Tipo: RED SOCIAL. Componentes obligatorios:
- Layout 3 columnas: nav izquierda, feed central, sugerencias/trending a la derecha.
- Composer: "¿Qué estás pensando?" con avatar y botón publicar funcional.
- Posts (mín. 6): avatar, nombre, handle, tiempo, texto, imagen opcional (picsum),
  botones like/comentar/compartir con contadores que se actualizan al click.
- Stories o carrusel horizontal arriba del feed si la referencia lo muestra.
- Panel de sugerencias con botón "Seguir" que cambia de estado.
Interacciones: publicar agrega el post arriba, like togglea color y contador, seguir/dejar de seguir.
```

---

## Comodín: producto que no matchea ninguno

Pegá esto en `{{ARQUETIPO}}`:

```
Tipo: NO CATALOGADO. Antes de implementar, listá internamente los 8-12 componentes
que un producto de este tipo siempre tiene, basándote en los líderes del mercado de
esa categoría, y tratalos como obligatorios.
```
