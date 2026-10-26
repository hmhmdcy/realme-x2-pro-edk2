from pathlib import Path
import ast
R=Path(__file__).resolve().parent
source=(R/'native-fixed-rgb.py').read_text().replace('k239-fixed-rgb-r14','k239-paired-r14').replace('/fixed-rgb-probe239','/paired-probe239').replace('k239_fixed_rgb_controls','k239_paired_controls').replace('fixed12-frame-rgb-debug-trace-armed','paired12-raw-rgb-debug-trace-armed')
source=source.replace("  program_exit=process.returncode", "  paired_same_request=True,raw_stream_geometry={k:data[k] for k in ['raw_width','raw_height','raw_stride']} if data and 'raw_width' in data else {},\n  program_exit=process.returncode")
assert 'paired_same_request=True' in source
ast.parse(source);(R/'native-paired.py').write_text(source)
start=(R/'start-fixed-rgb.py').read_text().replace('fixed-rgb-build-validation.json','paired-build-validation.json').replace('fixed-rgb-probe239','paired-probe239').replace('native-fixed-rgb.py','native-paired.py').replace('k239-fixed-rgb-r14','k239-paired-r14').replace('fixed-rgb-launch','paired-launch').replace('fixed12 RGB diagnostic running once','paired12 RAW/RGB diagnostic running once')
start=start.replace("assert json.loads((R/'baseline-validation.json').read_text())['current236_boot_verified']", "assert json.loads((R/'fixed-rgb-validation.json').read_text())['diagnostic_capture_completed']")
ast.parse(start);(R/'start-paired.py').write_text(start)
poll=(R/'poll-fixed-rgb.py').read_text().replace('k239-fixed-rgb-r14','k239-paired-r14').replace('fixed-rgb-validation.json','paired-validation.json').replace('fixed-rgb-poll','paired-poll').replace('fixed-rgb-parameter-log-lines-private.json','paired-parameter-log-lines-private.json').replace('fixed12 RGB diagnostic terminal','paired12 RAW/RGB diagnostic terminal')
ast.parse(poll);(R/'poll-paired.py').write_text(poll)
print('Prepared isolated paired request diagnostic, single RGB evidence remains unchanged')
