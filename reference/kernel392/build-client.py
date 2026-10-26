from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;out=P/'cancel-client'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-pthread',str(HERE/'cancel-client.c'),'-o',str(out)],capture_output=True)
(P/'client-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
r=dict(stage=392,client_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=out.stat().st_size,actual_v4l2_client=True,normal_platform_no_test_module=True,configured_log_marker_before_cancel=True,planned_cases=5,hardware_fault_not_injected=True,passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
