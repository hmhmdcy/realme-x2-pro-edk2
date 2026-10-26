"""Prepare the existing single-restart submission and fresh-identity FAT flasher."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel276/submit-restart.py').read_text().replace('k276','k288').replace('stage=276','stage=288').replace('k275-work','k276-work')
compile(s,'submit-restart.py','exec')
p=ROOT/'submit-restart.py';assert not p.exists();p.write_text(s)
