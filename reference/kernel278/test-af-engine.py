"""Compile and exercise the actual proposed production AF search state machine."""
from pathlib import Path
import hashlib,json,subprocess,sys
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt.isalnum();binary=P/('contrast-af-test-'+attempt);assert not binary.exists()
q=subprocess.run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(R/'contrast-af-test.cpp'),'-o',str(binary)],capture_output=True,timeout=90)
(P/('af-engine-build-'+attempt+'-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=30)
(P/('af-engine-test-'+attempt+'-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
d=dict(stage=278,**json.loads(q.stdout),source_sha256=hashlib.sha256((R/'contrast_af.h').read_bytes()).hexdigest(),cpp17_werror=True,asan=True,ubsan=True,physical_faults_not_injected=True)
(R/'af-engine-host-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
