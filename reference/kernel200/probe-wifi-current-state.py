from pathlib import Path
import importlib.util,json,subprocess
ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wifi200',ref/'host-before-newboot.py');wifi=importlib.util.module_from_spec(spec);spec.loader.exec_module(wifi)
try:p=wifi.ssh('python3 -',input=(ref/'inspect-camera-prepare-state.py').read_bytes(),timeout=35)
except Exception as error:
 if hasattr(error,'stdout'):(wifi.PRIVATE/'wifi-state-probe-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''))
 raise SystemExit('Current Wi-Fi state probe failed; private evidence retained')
(wifi.PRIVATE/'wifi-state-probe-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
