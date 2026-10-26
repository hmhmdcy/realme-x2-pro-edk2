#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out='/mnt/e/RealmeX2Pro edk2/reference/kernel73'
scripts/checkpatch.pl --no-tree --file drivers/gpu/drm/panel/panel-samsung-sofef03f.c > "$out/checkpatch.txt" 2>&1
/home/cy122/x2pro-linux/.venv-dtschema/bin/dt-doc-validate Documentation/devicetree/bindings/display/panel/samsung,sofef03f-m.yaml > "$out/binding-check.txt" 2>&1
cat "$out/checkpatch.txt"
