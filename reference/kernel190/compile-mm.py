from pathlib import Path
import hashlib,json,os,subprocess,time,shutil
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk');db=Path('/lib/apk/db/installed').read_bytes()
env=json.loads((out/'build-environment-private.json').read_text())
prior=out/'compile-resume-private.log'
if prior.exists():shutil.copyfile(prior,out/('compile-prior-'+str(time.time_ns())+'-private.log'))
with (out/'compile-resume-private.log').open('wb') as log:
 subprocess.run([str(sdk/'usr/bin/ninja'),'-C',str(out/'build'),'-j2','src/ModemManager'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200,env=env)
assert Path('/lib/apk/db/installed').read_bytes()==db
candidate=out/'build/src/ModemManager';assert candidate.is_file()
with (out/'candidate-elf-private.log').open('wb') as log:
 subprocess.run([str(sdk/'usr/bin/readelf'),'-h','-d',str(candidate)],stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
source=next((out/'source').iterdir())/'src/mm-shared-qmi.c'
report=dict(stage=190,candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),package_database_unchanged=True,compiled=True)
(out/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
