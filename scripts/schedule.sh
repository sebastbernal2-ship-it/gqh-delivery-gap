#!/usr/bin/env bash
# Install or remove the unattended memory timer for this repo on this machine.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
MARK="# gqh-delivery-gap-autoshare"
LINE="*/15 * * * * cd $ROOT && bash scripts/autoshare.sh >> .hippo/autoshare.log 2>&1 $MARK"

current="$(crontab -l 2>/dev/null || true)"
stripped="$(printf '%s\n' "$current" | grep -v "gqh-delivery-gap-autoshare" | grep -v '^$' || true)"

case "${1:-}" in
  install)
    printf '%s\n%s\n' "$stripped" "$LINE" | crontab -
    echo "installed: autoshare every 15 minutes"
    echo "$LINE"
    ;;
  uninstall)
    printf '%s\n' "$stripped" | crontab -
    echo "removed the autoshare timer"
    ;;
  *)
    echo "usage: schedule.sh install|uninstall" >&2
    exit 2
    ;;
esac
