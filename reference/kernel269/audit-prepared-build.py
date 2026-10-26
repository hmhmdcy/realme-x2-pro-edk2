"""Finish read-only DT validation after fixing the processed-schema filename."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269');U=Path('/home/cy122/x2pro-linux/upstream')
B=Path('/home/cy122/x2pro-linux/camera269-full-build-r1')
steps=json.loads((P/'prepare-state-private.json').read_text());assert len(steps)==3 and all(x['exit']==0 for x in steps)
before=json.loads((P/'initramfs-input-manifest-private.json').read_text())
s=(R/'prepare-build.py').read_text();tail=s[s.index("pp=P/'samurai.pp.dts'"):]
exec(compile(tail,'existing-prepare-validation','exec'))
