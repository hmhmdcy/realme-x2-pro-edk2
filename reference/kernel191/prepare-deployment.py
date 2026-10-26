from pathlib import Path
import json
import host
ref=Path(__file__).resolve().parent
assert json.loads((ref/'loc-injection-host-validation.json').read_text())['cases']==257
path=host.PRIVATE/'build-validation.json';host.download('/var/lib/samurai/k191-mm-build/build-validation.json',path)
build=json.loads(path.read_text());assert build['candidate_sha256']=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
(ref/'mm-build-validation.json').write_text(json.dumps(build,indent=2)+'\n')
source=(ref.parent/'kernel190/deploy-mm-candidate.py').read_text()
source=source.replace("out=Path('/var/lib/samurai/k190-mm-deploy')","out=Path('/var/lib/samurai/k191-mm-deploy')")
source=source.replace("build=Path('/var/lib/samurai/k190-mm-build');validation=json.loads((build/'candidate-validation.json').read_text())","build=Path('/var/lib/samurai/k191-mm-build');validation=json.loads((build/'build-validation.json').read_text())")
source=source.replace("validation['deployable_sha256']","validation['candidate_sha256']")
source=source.replace("mode=exe.stat().st_mode&0o777","mode=exe.stat().st_mode&0o777\nassert hashlib.sha256(old).hexdigest()=='fbc4084873e8e79d4bcdfa37982f4016a9e898f7123cecd37ba941ed55f27f69'")
source=source.replace("before['supported_assistance_data']==0","before['supported_assistance_data']==1")
source=source.replace("assert b'k190-mm-reinit-r2/daemon-debug-private.log' in args","assert b'k190-mm-deploy/daemon-debug-private.log' in args")
source=source.replace(".k190-new",".k191-new").replace('stage=190','stage=191')
assert source.count("k190-mm-reinit-r2")==1 and "k190-mm-build" not in source
compile(source,'deploy-mm-candidate.py','exec');(ref/'deploy-mm-candidate.py').write_text(source)
print('Reviewed deployment derived with working190 rollback and current source/binary gates')
