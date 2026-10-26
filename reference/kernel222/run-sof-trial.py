from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'sof-candidate-staging-validation.json').read_text())['experiment_not_yet_started']
code=(here/'native-sof-trial.py').read_bytes();p=host.ssh('python3 -',input=code,timeout=170)
(host.PRIVATE/'sof-trial-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'sof-candidate-native-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
