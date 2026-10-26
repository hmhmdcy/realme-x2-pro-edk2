"""Same nine real transport groups, plus the actual PM prepare fence."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent;PRIOR=HERE.parent/'apsd-final-transfer-candidate'
source=(PRIOR/'run-transfer-tests.py').read_text()
source=source.replace("(HERE/'test-transfer.c').read_text()","(PRIOR/'test-transfer.c').read_text().replace('input.dev=', 'input.event_dev=')")
source=source.replace("'run-transfer-tests.py']","'run-transfer-tests.py']")
source=source.replace("'test-transfer.c',", "")
position=source.index("flags=['-std=gnu11'")
source=source[:position]+'''fixture=fixture.replace(' return 0;\\n}', ' reset();input.pm_prepared=true;assert(run()==-ESHUTDOWN&&!map.reads&&!validations);puts("10 PM prepare fences final command before any read or transfer");\\n return 0;\\n}',1)
'''+source[position:]
source=source.replace('len(groups)==9','len(groups)==10')
ast.parse(source)
exec(compile(source,'<same-actual-transfer-current-IRQ-PM>','exec'),dict(__file__=str(HERE/'run-transfer-tests.py'),__name__='__main__',PRIOR=PRIOR))
