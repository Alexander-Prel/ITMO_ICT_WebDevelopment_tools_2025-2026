#!/usr/bin/env bash
set -euo pipefail
lab_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$lab_dir/.env" ]]; then
  echo 'Lr3/.env уже существует; настройки сохранены.'
  exit 0
fi
umask 077
python_bin="$lab_dir/../.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then python_bin=python3; fi
"$python_bin" - "$lab_dir/.env" <<'PY'
from pathlib import Path
import secrets
import sys

# Режим x не перезапишет уже существующий файл даже при одновременном запуске.
with Path(sys.argv[1]).open("x") as output:
    output.write(f"POSTGRES_PASSWORD={secrets.token_urlsafe(24)}\n")
    output.write(f"SECRET_KEY={secrets.token_urlsafe(48)}\n")
    output.write("API_PORT=8003\nPARSER_PORT=8004\nPOSTGRES_PORT=5433\n")
print("Создан Lr3/.env. Значения секретов не выводятся в терминал.")
PY
