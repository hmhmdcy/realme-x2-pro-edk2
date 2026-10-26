#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
ref='/mnt/e/RealmeX2Pro edk2/reference/kernel74'
scripts/checkpatch.pl --no-tree --no-signoff --ignore COMMIT_MESSAGE "$ref/handoff-candidate.patch" > "$ref/checkpatch.txt" 2>&1
python3 "$ref/validate-initramfs.py"
cat "$ref/checkpatch.txt"
