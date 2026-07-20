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

## 2. UI — completar los ABM

- Que **todas** las vistas sean ABM completo (alta / edición inline / baja): roles, tracks,
  tareas, knowledge y personas. Auditar y cerrar lo que falte editar.
- Probar cada flujo end-to-end, incluido cambiar la fecha de bench y ver que dispara el
  mensaje proactivo (el bug anterior lo arregló el hardening; verificarlo en vivo).

## 3. Feature — asignar responsables

- Asignar / quitar responsables por track desde la UI y confirmar que el reporte EOD les
  llega (archivo + mensaje proactivo del bot).
- Poder responderle a un responsable desde el flujo.

## Carryover del repo original (workshop Labs)

- **Lab 1** (local, sin SDK): hecho y preservado (job `onboarding` en CI lo protege).
- **Lab 2** (Strands + Bedrock real): código listo (`bench/strands_agent.py`), se corre local.
- **Lab 3** (accelerator AWS `sample-strands-agentcore-starter`): sin empezar — es el item de
  carryover más grande, requiere los servicios de AWS del punto 1.
