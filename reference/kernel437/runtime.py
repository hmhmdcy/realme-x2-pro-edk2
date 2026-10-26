from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel436/runtime.py').read_text().replace("'k436-tone-domain-'","'k437-awb-history-'")
exec(compile(source,str(HERE/'runtime.py'),'exec'))
