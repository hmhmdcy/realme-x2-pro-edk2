from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel287/inspect-layering.py').read_text().replace('k276-work','k293-work').replace('stage=287','stage=293').replace('reference/kernel287/layering','reference/kernel293/layering')
p=ROOT/'inspect-layering.py';assert not p.exists();p.write_text(s)
