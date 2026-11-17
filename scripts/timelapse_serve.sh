#!/usr/bin/env bash
# Поднимает сайт на заданном коммите в отдельном worktree для скриншота.
# Использование: scripts/timelapse_serve.sh <commit> <port>
# Печатает URL и путь к worktree; останавливать: kill <pid из вывода> или Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")/.."
COMMIT="$1"; PORT="$2"
SHORT=$(git rev-parse --short "$COMMIT")
WT="/home/nikita/.hermes/cache/scratch/timelapse/$SHORT"
git worktree add --force "$WT" "$COMMIT" 2>/dev/null || true
cd "$WT"
uv sync -q
export DJANGO_DEBUG=1
export DEMO_STUDENT_A_PASSWORD=$(grep '^demo_a=' /home/nikita/Projects/mgimo_new_decanait/.secrets/demo_passwords.txt | cut -d= -f2)
export DEMO_STUDENT_B_PASSWORD=$(grep '^demo_b=' /home/nikita/Projects/mgimo_new_decanait/.secrets/demo_passwords.txt | cut -d= -f2)
export DEMO_STAFF_PASSWORD=$(grep '^demo_staff=' /home/nikita/Projects/mgimo_new_decanait/.secrets/demo_passwords.txt | cut -d= -f2)
uv run python manage.py migrate -q --noinput
uv run python manage.py seed_demo > /dev/null
echo "WORKTREE=$WT"
exec uv run python manage.py runserver "127.0.0.1:$PORT" --noreload
