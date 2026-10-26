"""Compile the actual proposed production helper with ASan and UBSan."""
from pathlib import Path
import hashlib,json,subprocess
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
binary=P/'focus-stats-test';assert not binary.exists()
q=subprocess.run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(R/'focus-stats-test.cpp'),'-o',str(binary)],capture_output=True,timeout=90)
(P/'focus-stats-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=90)
(P/'focus-stats-test-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
report=dict(stage=277,**json.loads(q.stdout),cpp17_werror_clean=True,asan=True,ubsan=True,
 source_sha256=hashlib.sha256((R/'focus_stats.h').read_bytes()).hexdigest(),physical_camera_not_tested_by_host_cases=True)
(R/'focus-stats-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
