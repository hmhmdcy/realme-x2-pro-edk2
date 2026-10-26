"""Verify the complete r29 artifacts using unchanged360 IPA contracts."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
script=(HERE.parent/'kernel360/collect-packages.py').read_text().replace('360','362').replace('r28','r29').replace('r23','r24')
# The mathematical reference files and executable are unchanged; no need to copy
# factory data or rebuild their independent numerical reference here.
script=script.replace("cases=json.loads((P/'cases-private.json').read_text())", "cases=json.loads((P.parent/'kernel360/cases-private.json').read_text())")
script=script.replace("relative=Path('/private/camss362-contract')", "relative=Path('/private/camss360-contract')")
script=script.replace("source.parent/'camss362-contract'", "source.parent/'camss360-contract'")
exec(compile(script,str(HERE/'collect-packages.py'),'exec'))
