from pathlib import Path
here=Path(__file__).resolve().parent
code=(here.parent/'kernel220/collect-final-evidence.py').read_text().replace('k220-','k221-').replace('stage=220','stage=221')
compile(code,'collect-final-evidence221','exec');(here/'collect-final-evidence.py').write_text(code)
print('K221_EXPORT_PREPARED')
