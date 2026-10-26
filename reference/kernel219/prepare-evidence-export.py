"""Retain native diagnostics privately, excluding duplicate transfer containers."""
from pathlib import Path
here=Path(__file__).resolve().parent
text=(here.parent/'kernel218/collect-final-evidence.py').read_text()
text=text.replace("base=root/'k218-baseline'","base=root/'k219-runtime'")
text=text.replace("k218-","k219-").replace("stage=218","stage=219")
text=text.replace("['probe.gz','runtime.tar.gz']","['probe.gz','runtime.tar.gz','bundle-private.tar.gz']")
compile(text,'evidence-export219','exec');(here/'collect-final-evidence.py').write_text(text)
print('Current219 private evidence export prepared; no archive created yet')
