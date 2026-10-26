from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel321/build-candidate.py').read_text().replace('libcamera321-lsc-built','libcamera332-cct-built').replace('libcamera-before321','libcamera-before332').replace('stage=321','stage=332')
exec(compile(s,str(HERE/'build-candidate.py'),'exec'),dict(__file__=str(HERE/'build-candidate.py'),__name__='__main__'))
