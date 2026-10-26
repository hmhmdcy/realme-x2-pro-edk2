"""Reuse original-key USB transport."""
from pathlib import Path
import importlib.util
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel313');PRIVATE.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('host312',Path(__file__).resolve().parents[1]/'kernel312/host.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
raw_ssh=old.raw_ssh
# Read-only calls need no repeated boot comparison. The capture worker checks
# boot/module compatibility once before opening the experiment.
ssh=raw_ssh
