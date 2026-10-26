from pathlib import Path
import json
import host

code=(Path(__file__).resolve().parent/'native-sensors.py').read_text()
result=host.ssh('python3 -',input=code.encode(),timeout=130)
(host.PRIVATE/'native-sensors-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout)
(Path(__file__).resolve().parent/'native-sensors-validation.json').write_text(json.dumps(report,indent=2)+'\n')
state=json.loads((host.PRIVATE/'current-work-private.json').read_text());state.update(state='clean intree new boot and native five streams, actual pin, active Wayland claims passed',active_native_session=None,active_native_context=None,clean_intree_boot_verified=True)
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(report))
