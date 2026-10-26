"""Prepare fresh second207 boot queries and one GNSS test; do not run them."""
from pathlib import Path
import ast

here = Path(__file__).resolve().parent
reference = here.parent.parent
prepare = (reference / 'kernel206/prepare-gnss-session.py').read_text()
prepare = prepare.replace('k206', 'k207r2').replace('stage=206', 'stage=207')
prepare = prepare.replace('k205r2-runtime', 'k207r2-runtime')
prepare = prepare.replace("here.parent / 'kernel", "here.parent.parent / 'kernel")
prepare = prepare.replace("'k207r2-gnss-context'", "'k207r2-gnss-context'")
prepare = prepare.replace("tftp_runtime_replaced_before_session=True,new_tftp_startup_not_yet_tested=True,", "tftp_runtime_replaced_before_session=True,new_tftp_startup_not_yet_tested=False,stock_mcfg_auto_staging_verified_before_session=True,")
prepare = prepare.replace(".replace('stage=204', 'stage=207')", ".replace('stage=204', 'stage=207')")
ast.parse(prepare)
(here / 'prepare-gnss-session.py').write_text(prepare)
for name in ['query-pdc-readonly.py', 'query-pdc-details.py']:
    source = (here.parent / name).read_text().replace('k207', 'k207r2')
    source = source.replace('current_r2_boot_verified=True', 'current_second207_boot_verified=True')
    ast.parse(source)
    (here / name).write_text(source)
print('Read-only PDC and finite GNSS test sources prepared. No sessions or queries started.')
