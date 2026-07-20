# Bench Assistant — Roadmap

Todo corre **local**: el servicio en localhost, el bot por dev tunnel a Teams, y los
servicios de AWS (Bedrock) se consumen **desde local** con la sesión SSO. No se despliega
nada en AWS ni se publica el bot en el tenant de Endava (no tenemos esos accesos aún).

Estado: `feature/bench` con el hardening del piloto integrado. 32 tests en verde.

## 1. Servicios de AWS (desde local)

- **Bedrock** ya se usa desde local para el chat conversacional y el resumen del ciclo diario.
- **DynamoDB** como store, detrás de un flag `BENCH_STORAGE=sqlite|dynamodb` (default `sqlite`,
  así nunca rompe la demo). La costura en `bench/tools/state.py` + `db.py` ya está aislada.
- **Bedrock Knowledge Base + S3** para RAG sobre los PDF de perfil (journey B3): que el agente
  responda con citas en vez del match por tags actual.

## 2. UI — completar el backoffice local

- Cerrar el contrato de requisitos en `PRODUCT_SPEC.md` y `BACKOFFICE_SPEC.md`.
- Que **todas** las vistas sean descubribles y tengan ABM completo (alta / edición inline / baja o
  archivado): roles, tracks, tareas, knowledge, responsables y personas. En particular faltan el
  mantenimiento del ciclo de vida de personas y la edición de responsables.
- Mostrar en el detalle de persona el estado de acceso/approval simulado y el action log; nunca
  conceder permisos reales desde esta UI local.
- Probar cada flujo end-to-end, incluido cambiar la fecha de bench y ver que dispara la evaluación
  inmediata del mensaje proactivo.

## 3. Feature — asignar responsables

- Asignar / editar / quitar responsables por track desde la UI y confirmar que el reporte EOD les
  llega (archivo + mensaje proactivo del bot).
- Poder responderle a un responsable desde el flujo.

## Carryover del repo original (workshop Labs)

- **Lab 1** (local, sin SDK): hecho y preservado (job `onboarding` en CI lo protege).
- **Lab 2** (Strands + Bedrock real): código listo (`bench/strands_agent.py`), se corre local.
- **Lab 3** (accelerator AWS `sample-strands-agentcore-starter`): sin empezar — es el item de
  carryover más grande, requiere los servicios de AWS del punto 1.
