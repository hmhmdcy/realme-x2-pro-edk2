from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel341/build-candidate.py').read_text().replace('stage=341','stage=349')
exec(compile(s,str(HERE/'build-candidate.py'),'exec'),dict(__file__=str(HERE/'build-candidate.py'),__name__='__main__'))
