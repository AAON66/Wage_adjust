#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

repo_root="$(pwd)"
proof_path=".planning/phases/19-celery-redis/19-03-runtime-proof.log"
compose_file="$(mktemp /tmp/phase19-compose.XXXXXX.yml)"
project_name="wage_adjust_phase19_proof"
cat > "$compose_file" <<EOF
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
  backend:
    build: ${repo_root}
    command: uvicorn backend.app.main:app --host 0.0.0.0 --port 8011 --reload
    env_file:
      - ${repo_root}/.env
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ${repo_root}:/app
  celery-worker:
    build: ${repo_root}
    command: celery -A backend.app.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - ${repo_root}/.env
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ${repo_root}:/app
volumes:
  redis_data:
EOF
compose_cmd=(docker compose --project-name "$project_name" -f "$compose_file")
mkdir -p "$(dirname "$proof_path")"
: > "$proof_path"

cleanup() {
  "${compose_cmd[@]}" down --remove-orphans >/dev/null 2>&1 || true
  rm -f "$compose_file"
}
trap cleanup EXIT

# base command: docker compose up -d redis celery-worker
"${compose_cmd[@]}" up -d redis celery-worker

ready=0
for _ in $(seq 1 60); do
  if "${compose_cmd[@]}" logs celery-worker 2>&1 | grep -q 'ready\.'; then
    ready=1
    break
  fi
  sleep 1
done

if [[ "$ready" -ne 1 ]]; then
  "${compose_cmd[@]}" logs celery-worker --tail=200 >> "$proof_path" 2>&1 || true
  echo "Celery worker did not report ready. within 60 seconds" >&2
  exit 1
fi

# base command: docker compose run --rm backend python scripts/celery_runtime_probe.py
"${compose_cmd[@]}" run --rm backend python scripts/celery_runtime_probe.py >> "$proof_path"
"${compose_cmd[@]}" logs celery-worker --tail=200 >> "$proof_path" 2>&1

grep -q 'PHASE19_TASK_RESULT={"db_check": true, "status": "ok"}' "$proof_path"
grep -q 'Task tasks.db_health_check\[' "$proof_path"
grep -q 'succeeded in' "$proof_path"

echo 'PHASE19_PROOF=ok' >> "$proof_path"
