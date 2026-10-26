from pathlib import Path
import hashlib,json,shutil
ref=Path(__file__).resolve().parent;previous=ref.parent/'kernel194';out=Path('/mnt/e/edk2-samurai-out/kernel195');oldout=out.parent/'kernel194'
s=(previous/'build-pmic-module.py').read_text().replace('kernel194','kernel195').replace('stage=194','stage=195')
s=s.replace("'# CONFIG_OF_SAMURAI_FRONT_IDENTIFY is not set'},delta","'# CONFIG_OF_SAMURAI_FRONT_IDENTIFY is not set','# CONFIG_OF_SAMURAI_PMIC_FIXTURE is not set'},delta").replace('first_attempt_stopped_on_two_new_default_disabled_config_comments=True','three_new_default_disabled_config_comments_only=True')
(ref/'build-pmic-module.py').write_text(s)
record=json.loads((previous/'pmic-fixture-build-validation.json').read_text());p=oldout/'samurai-pmic-fixture.ko';assert hashlib.sha256(p.read_bytes()).hexdigest()==record['module_sha256'];shutil.copyfile(p,out/p.name)
record.update(stage=195,reused_unchanged_from_stage194=True);(ref/'pmic-fixture-build-validation.json').write_text(json.dumps(record,indent=2)+'\n')
for name in ['stage-pmic-fixture.py','probe-pmic-driver-cold.py','probe-pmic-driver-warm.py','probe-q-reset-address.py','final-health.py','export-native.py']:
 s=(previous/name).read_text().replace('k194-','k195-').replace('stage=194','stage=195')
 (ref/name).write_text(s)
print('New module build, unchanged fixture and fresh native evidence paths prepared')
