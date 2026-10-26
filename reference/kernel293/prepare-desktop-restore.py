from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel273/restore-desktop.py').read_text().replace('k273','k293').replace('stage=273','stage=293')
s=s.replace("['6-0010','7-0010','8-002d','9-0010']","['8-0010','7-0010','6-002d','9-0010']")
p=ROOT/'restore-desktop.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared one bounded desktop start; no SSC restart or permanent dependency edit.')
