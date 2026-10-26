from pathlib import Path
import json,subprocess,os
os.umask(0o077);out=Path('/var/lib/samurai/k197-tools-dryrun');out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k197-baseline/boot-id-private.txt').read_bytes()
p=subprocess.run(['apk','add','--simulate','v4l-utils'],capture_output=True,text=True,timeout=60);(out/'simulate-private.txt').write_text(p.stdout+p.stderr);print(json.dumps(dict(returncode=p.returncode,simulation=p.stdout+p.stderr)))
