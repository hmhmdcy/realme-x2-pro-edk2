set -euo pipefail
cd /home/cy122/edk2-samurai/repo
git add -- Platform/Realme/sm8150/HANDOVER-NEXT.md Platform/Realme/sm8150/RX-CONSOLE.md Platform/Realme/sm8150/FLYWHEEL.md Platform/Realme/sm8150/DOCS-INDEX.md Platform/Realme/sm8150/linux-port/docs/EUD-TERMINAL.md Platform/Realme/sm8150/sessions/54-console-rx-regression-and-host-counter-audit.md Platform/Realme/sm8150/reference/rx54
python3 /mnt/e/edk2-samurai-out/rx54/check-staged.py
git diff --cached --check
git diff --cached --stat
