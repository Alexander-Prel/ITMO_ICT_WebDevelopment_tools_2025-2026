#!/usr/bin/env bash
set -euo pipefail
lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -f "$lab_dir/.env" ]]; then
  echo 'Сначала выполни bash setup.sh из папки Lr3.' >&2
  exit 1
fi

# На macOS Docker Desktop может быть установлен без добавления CLI в PATH.
desktop_bin=/Applications/Docker.app/Contents/Resources/bin
if [[ -d "$desktop_bin" ]]; then export PATH="$desktop_bin:$PATH"; fi
if ! command -v docker >/dev/null 2>&1; then
  echo 'Docker CLI не найден. Установи и запусти Docker Desktop.' >&2
  exit 1
fi
compose_cmd=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  desktop_compose=/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose
  if [[ -x "$desktop_compose" ]]; then compose_cmd=("$desktop_compose");
  else echo 'Docker Compose не найден.' >&2; exit 1; fi
fi
exec "${compose_cmd[@]}" --env-file "$lab_dir/.env" -f "$lab_dir/docker-compose.yml" "$@"
