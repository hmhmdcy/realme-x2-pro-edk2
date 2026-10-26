from pathlib import Path
import ast

here = Path(__file__).resolve().parent
source = (here.parent / 'inspect-bootstrap.py').read_text()
source = source.replace('k207-runtime', 'k207r2-runtime').replace('k207-before-reboot', 'k207r2-before-reboot').replace('k207-bootstrap-inspection', 'k207r2-bootstrap-inspection')
source = source.replace('ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd', '854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f')
source = source.replace("(out / 'summary.json').write_text", """mdtime = [line for line in text.splitlines() if '/modem_pr/mcfg/configs/mcfg_sw/mdtime.txt' in line]
mcfg = [line for line in text.splitlines() if '/modem_pr/mcfg/' in line]
(out / 'stock-mcfg-tftp-lines-private.txt').write_text('\\n'.join(mcfg) + '\\n')
result.update(reboot_cycle=2, stock_mcfg_173_files_auto_staged=True,
    mdtime_read_requests=sum('read request for ' in line for line in mdtime),
    mdtime_opened_for_reading=sum('opened for reading' in line for line in mdtime),
    mdtime_open_errors=sum(any(word in line.lower() for word in ['reject', 'unable to open', 'failed to open']) for line in mdtime),
    stock_mcfg_read_requests=sum('read request for ' in line for line in mcfg),
    stock_mcfg_opened_for_reading=sum('opened for reading' in line for line in mcfg),
    stock_mcfg_open_errors=sum(any(word in line.lower() for word in ['reject', 'unable to open', 'failed to open']) for line in mcfg))
(out / 'summary.json').write_text""")
ast.parse(source)
(here / 'inspect-bootstrap.py').write_text(source)
(here / 'run-native.py').write_bytes((here.parent / 'run-native.py').read_bytes())
print('Second207 boot inspection prepared; no device operation.')
