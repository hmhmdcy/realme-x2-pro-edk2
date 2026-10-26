from pathlib import Path
import json,shutil,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k197-baseline/boot-id-private.txt').read_bytes()
p=Path('/var/lib/samurai/k197-tools-install/install-private.txt');print(json.dumps(dict(log=p.read_text() if p.exists() else None,tools={n:shutil.which(n) for n in ['media-ctl','v4l2-ctl']},apk_processes=subprocess.check_output(['pgrep','-x','apk'],text=True).strip() if subprocess.run(['pgrep','-x','apk'],capture_output=True).returncode==0 else '',repositories=Path('/etc/apk/repositories').read_text())))
