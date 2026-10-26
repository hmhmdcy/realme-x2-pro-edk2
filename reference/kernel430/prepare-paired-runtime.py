"""Reuse the bounded paired-source transaction with the checked topology cohort."""
from pathlib import Path
import ast,runpy,sys
HERE=Path(__file__).resolve().parent
client=(HERE.parent/'kernel429/pd10-ipe.c').read_text().replace('71488','46128')
(HERE/'pd10-ipe.c').write_text(client)
text=(HERE.parent/'kernel429/build-client.py').read_text().replace('stage=429','stage=430');(HERE/'build-client.py').write_text(text)
runpy.run_path(str(HERE/'build-client.py'),run_name='__main__')
text=(HERE.parent/'kernel429/prepare-runtime.py').read_text()
text=text.replace("assert build['attempt']==3", "assert build['attempt']==1")
text=text.replace("(P/'postboot-adoption-private.json')", "(P.parent/'kernel429/postboot-adoption-private.json')")
text=text.replace("(P/'runtime-collected-r3/state.json')", "(P.parent/'kernel429/runtime-collected-r3/state.json')")
text=text.replace('k429-pd10-ipe-','k430-dc-topology-').replace("'stage':429","'stage':430")
ast.parse(text);(HERE/'prepare-runtime.py').write_text(text)
(HERE/'runtime.py').write_text((HERE.parent/'kernel429/runtime.py').read_text().replace('k429-pd10-ipe-','k430-dc-topology-'))
sys.argv=[str(HERE/'prepare-runtime.py'),'r1'];runpy.run_path(str(HERE/'prepare-runtime.py'),run_name='__main__')
