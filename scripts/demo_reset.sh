#!/usr/bin/env bash
# Reset Bench data for a clean demo run — WITHOUT dropping any AWS structure.
# It deletes local state and EMPTIES the AWS data (items/objects), but never
# deletes the DynamoDB tables or the S3 bucket, so nothing has to be recreated
# (no waiting). The catalog re-seeds automatically when the service starts.
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
AWS="aws --region $REGION --profile $PROFILE"

echo "== 1. Local state (SQLite catalog + people, chat memory, reports) =="
rm -f  "$PROGRESS/bench.db"          && echo "  removed bench.db (people + tasks; catalog re-seeds on start)"
rm -f  "$PROGRESS/chat-memory.db"    && echo "  removed chat-memory.db (agent memory)"
rm -rf "$PROGRESS/reports"           && echo "  removed local reports"

echo "== 2. DynamoDB notifications — EMPTY items (table kept) =="
ids=$($AWS dynamodb scan --table-name "$PREFIX-notifications" \
        --projection-expression id --query "Items[].id.S" --output text 2>/dev/null)
if [ -n "${ids:-}" ]; then
  for id in $ids; do
    $AWS dynamodb delete-item --table-name "$PREFIX-notifications" \
      --key "{\"id\":{\"S\":\"$id\"}}" >/dev/null 2>&1
  done
  echo "  emptied $PREFIX-notifications"
else
  echo "  $PREFIX-notifications already empty or absent (ok)"
fi

echo "== 3. conversation-refs — KEPT on purpose =="
echo "  (so you do NOT need to message the bot 'hola' again after the reset)"

echo "== 4. S3 documents — empty contents (bucket kept) =="
$AWS s3 rm "s3://$BUCKET" --recursive >/dev/null 2>&1 \
  && echo "  emptied s3://$BUCKET" || echo "  s3://$BUCKET empty or unavailable (ok)"

echo
echo "Done — no AWS structures were dropped. Start the service:"
echo "  uv run --group ui --extra agentic uvicorn bench.webapp:app --reload"
echo "Then onboard from the web, or seed one via CLI:"
echo "  uv run python -m bench.app start --employee \"Pedro Garateguy\" \\"
echo "    --email pedro.garateguy@endava.com --profile backend-dev --track aws-backend-track"
