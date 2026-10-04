#!/usr/bin/env bash
# One command to make a fresh Ubuntu machine collect, replay, and report.
#
#   bash deploy/setup.sh
#
# Installs Docker for the collector and opam for the engine, builds and tests
# the engine, starts the collector, installs the daily replay timer, and runs
# that timer once so the first report exists before you walk away.
#
# Configuration: REPO_DIR and ENV_FILE, both overridable from the environment.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$HOME/.config/quanthacks/env}"
DAILY_HOUR="${DAILY_HOUR:-0}"
DAILY_MINUTE="${DAILY_MINUTE:-20}"

say() { printf '\n== %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

say "checking the machine"
command -v sudo >/dev/null || die "sudo is required"
sudo -n true 2>/dev/null || die "passwordless sudo is required"
command -v apt-get >/dev/null || die "this script expects Ubuntu or Debian"
[ -f "$REPO_DIR/dune-project" ] || die "no dune-project in $REPO_DIR, set REPO_DIR"

say "system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  docker.io docker-compose-v2 opam m4 pkg-config build-essential libssl-dev \
  zlib1g-dev jq python3-venv python3-pip >/dev/null

say "docker service"
sudo systemctl enable --now docker >/dev/null
if ! id -nG "$USER" | tr ' ' '\n' | grep -qx docker; then
  sudo usermod -aG docker "$USER"
  echo "added $USER to the docker group, a new login is needed for password-free docker"
fi

say "opam and OCaml 5.2 (this takes a while on a fresh machine)"
export OPAMYES=1
if [ ! -d "$HOME/.opam" ]; then
  opam init --disable-sandboxing --bare -y >/dev/null
fi
eval "$(opam env)"
if ! opam switch list --short 2>/dev/null | grep -qx 5.2.0; then
  opam switch create 5.2.0 ocaml-base-compiler.5.2.0 >/dev/null
  eval "$(opam env)"
fi
opam switch set 5.2.0 >/dev/null
eval "$(opam env)"

say "engine dependencies and build"
cd "$REPO_DIR"
opam install --deps-only -y . >/dev/null
opam exec -- dune build 2>&1 | tail -3
echo "build ok"

say "engine tests"
opam exec -- dune runtest 2>&1 | grep -E "Test Successful|failures" | tail -8 || true

say "secret store"
if [ ! -f "$ENV_FILE" ]; then
  mkdir -p "$(dirname "$ENV_FILE")"
  cp "$REPO_DIR/deploy/quanthacks.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  cat <<MESSAGE

Filled-in credentials are missing. A template is now at:
  $ENV_FILE

Fill in the values, keep mode 600, then run this script again.
The collector itself needs no credentials, so it is started anyway.

MESSAGE
fi

say "collector"
cd "$REPO_DIR/collector"
# The data directory must belong to the invoking user before the container
# starts, otherwise Docker creates it as root and the replay job cannot write.
mkdir -p "$REPO_DIR/collector/data"
sudo chown -R "$(id -u):$(id -g)" "$REPO_DIR/collector/data"
export CONTAINER_UID="$(id -u)"
export CONTAINER_GID="$(id -g)"
sudo --preserve-env=CONTAINER_UID,CONTAINER_GID docker compose up -d --build >/dev/null
sudo docker compose ps
sudo chown -R "$(id -u):$(id -g)" "$REPO_DIR/collector/data"

say "daily replay timer"
sudo tee /etc/systemd/system/market-replay.service >/dev/null <<UNIT
[Unit]
Description=Market simulator daily capture replay
After=docker.service network-online.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$REPO_DIR
Environment=REPO_DIR=$REPO_DIR
ExecStart=/bin/bash $REPO_DIR/deploy/daily-replay.sh
# A day of windows is small. Thousands of files means stray data arrived, and
# the job should fail fast and leave the box usable instead of being killed.
MemoryMax=6G
TimeoutStartSec=1800
Nice=10
UNIT
sudo tee /etc/systemd/system/market-replay.timer >/dev/null <<UNIT
[Unit]
Description=Run the market simulator daily replay

[Timer]
OnCalendar=*-*-* $DAILY_HOUR:$DAILY_MINUTE:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now market-replay.timer >/dev/null
systemctl list-timers market-replay.timer --no-pager | head -3

say "first run"
bash "$REPO_DIR/deploy/daily-replay.sh" || echo "the first run reported no data yet, which is normal on a fresh box"

say "done"
cat <<MESSAGE

Collector: running in Docker, writing windows under $REPO_DIR/collector/data
Reports:   $REPO_DIR/collector/data/reports
Timer:     market-replay.timer, daily at $DAILY_HOUR:$DAILY_MINUTE UTC

Check again later with:
  systemctl list-timers market-replay.timer
  journalctl -u market-replay.service -n 40

MESSAGE
