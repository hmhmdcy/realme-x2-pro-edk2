from pathlib import Path
import hashlib,json,subprocess
import host
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-broadcast'
q=subprocess.run(['chroot',str(SDK),'ninja','-C','/work/pipewire263-broadcast/build','-j2','src/tools/pw-metadata'],capture_output=True)
(host.PRIVATE/'metadata-tool-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()[-1800:]
p=W/'build/src/tools/pw-metadata';assert p.is_file();data=p.read_bytes();(host.PRIVATE/'pw-metadata').write_bytes(data)
code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k265-tools/pw-metadata');assert not p.exists();p.write_bytes(sys.stdin.buffer.read());p.chmod(0o755)"
import shlex
host.ssh('python3 -c '+shlex.quote(code),input=data)
report=dict(stage=265,tool='pw-metadata',source_version='1.6.9',sha256=hashlib.sha256(data).hexdigest(),private_tool_only_not_system_install=True)
(Path(__file__).parent/'metadata-tool-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
