#!/usr/bin/env bash
# Reset ALL Bench data for a clean demo run.
# Wipes local state (SQLite, chat memory, reports) and the AWS demo data
# (DynamoDB tables + S3 documents). The catalog (roles/tracks/tasks/knowledge)
# re-seeds automatically the next time the service starts.
#
# Usage:  bash scripts/demo_reset.sh
# Stop the service (Ctrl+C) BEFORE running this.
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROGRESS="$ROOT/.local-progress"
REGION="${AWS_REGION:-us-west-2}"
PROFILE="${AWS_PROFILE:-pedro.garateguy.endava}"
BUCKET="${BENCH_DOCS_S3_BUCKET:-bench-docs-mvp}"
PREFIX="${BENCH_DYNAMODB_PREFIX:-bench}"

echo "== 1. Local state (SQLite, chat memory, reports) =="
rm -f  "$PROGRESS/bench.db"          && echo "  removed bench.db (catalog + people + tasks)"
rm -f  "$PROGRESS/chat-memory.db"    && echo "  removed chat-memory.db (agent conversation memory)"
rm -rf "$PROGRESS/reports"           && echo "  removed local reports"

echo "== 2. DynamoDB tables (recreate on demand) =="
for t in "$PREFIX-notifications" "$PREFIX-conversation-refs"; do
  aws dynamodb delete-table --table-name "$t" --region "$REGION" --profile "$PROFILE" \
    >/dev/null 2>&1 && echo "  deleted $t" || echo "  $t not present (ok)"
done

echo "== 3. S3 documents (keep the bucket, empty its contents) =="
aws s3 rm "s3://$BUCKET" --recursive --region "$REGION" --profile "$PROFILE" \
  >/dev/null 2>&1 && echo "  emptied s3://$BUCKET" || echo "  s3://$BUCKET empty or unavailable (ok)"

echo
echo "Done. Start the service (catalog re-seeds automatically):"
echo "  uv run --group ui --extra agentic uvicorn bench.webapp:app --reload"
echo "Then onboard people from the web (Onboard to bench) or seed a couple via CLI:"
echo "  uv run python -m bench.app start --employee \"Pedro Garateguy\" \\"
echo "    --email pedro.garateguy@endava.com --profile backend-dev --track aws-backend-track"
