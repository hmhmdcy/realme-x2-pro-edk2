"""Reuse the reviewed new-boot preflight with a distinct tele window namespace."""
from pathlib import Path
import importlib.util
import re
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('preflight461_for467',HERE.parent/'kernel461/preflight-handoff.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def window_valid(value):
    assert re.fullmatch(r'k467-tele-r([1-9]|1[0-9]|20)',value),'Unsupported tele window'

base.window_valid=window_valid
base.PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel467/preflight')
if __name__=='__main__':
    assert '--window-id' in sys.argv and '--self-test' not in sys.argv
    base.main()
