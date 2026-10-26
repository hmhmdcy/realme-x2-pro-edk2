from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
runner=(here/'native-control-runner.py').read_bytes()
code="from pathlib import Path;p=Path('/var/lib/samurai/k223-sof-modules/control-runner.py');assert not p.exists();p.write_bytes("+repr(runner)+")"
host.ssh('python3 -',input=code.encode(),timeout=25)
p=host.ssh('python3 -',input=(here/'native-control-trial.py').read_bytes(),timeout=210)
(host.PRIVATE/'control-trial-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'control-snapshot-native-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
