from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel340/legacy-regression.py').read_text().replace('camss340-contract','camss341-contract').replace('stage=340','stage=341')
exec(compile(s,str(HERE/'legacy-regression.py'),'exec'),dict(__file__=str(HERE/'legacy-regression.py'),__name__='__main__'))
