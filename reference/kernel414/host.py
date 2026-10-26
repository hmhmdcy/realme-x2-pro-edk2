"""Reuse offline host configuration; stage414 never opens the phone."""
from pathlib import Path
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel414')
PRIVATE.mkdir(mode=0o700,exist_ok=True)
