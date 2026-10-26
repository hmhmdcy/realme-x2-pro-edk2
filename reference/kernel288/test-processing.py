"""Retain the existing actual processing/lifecycle regression on the PIX candidate."""
from pathlib import Path

previous = Path(__file__).resolve().parents[1]/'kernel287/test-demux-mnds.py'
s = previous.read_text().replace('/mnt/e/edk2-samurai-out/kernel287','/mnt/e/edk2-samurai-out/kernel288')
s = s.replace("(ROOT/'demux-mnds-tests.c')", "(ROOT.parent/'kernel287/demux-mnds-tests.c')")
s = s.replace("'stage=287'", "'stage=288'")
exec(compile(s,str(previous),'exec'),globals())
