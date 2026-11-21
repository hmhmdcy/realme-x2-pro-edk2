#!/usr/bin/env python3
"""Report real DTS properties (ignore text inside comments)."""
import re
import sys

def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//.*", "", s)
    return s

for path in sys.argv[1:]:
    src = strip_comments(open(path, encoding="utf-8").read())
    prop = re.search(r"^\s*flash-leds\s*=\s*<", src, re.M)
    lens = re.search(r"^\s*lens-focus\s*=\s*<", src, re.M)
    print(f"{path.split('/')[-1]:26s} flash-leds={'yes' if prop else 'no '} "
          f"lens-focus={'yes' if lens else 'no'}")
