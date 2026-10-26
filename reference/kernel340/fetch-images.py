from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel335/fetch-images.py').read_text().replace('k335-ccm-','k340-aec-ccm-').replace('six-phase','four-phase')
exec(compile(s,str(HERE/'fetch-images.py'),'exec'),dict(__file__=str(HERE/'fetch-images.py'),__name__='__main__'))
