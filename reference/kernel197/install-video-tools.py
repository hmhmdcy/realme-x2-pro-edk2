from pathlib import Path
import hashlib,json,os,re,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k197-tools-install';out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k197-baseline/boot-id-private.txt').read_bytes()
plan=(root/'k197-tools-dryrun/simulate-private.txt').read_text();assert len(re.findall(r'Installing ',plan))==2 and 'Upgrading ' not in plan and 'Removing ' not in plan and 'v4l-utils-libs (1.32.0-r1)' in plan
before=hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest();assert before=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
p=subprocess.run(['apk','add','v4l-utils=1.32.0-r1','v4l-utils-libs=1.32.0-r1'],capture_output=True,text=True,timeout=90);(out/'install-private.txt').write_text(p.stdout+p.stderr);assert p.returncode==0 and hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()==before
versions={}
for name in ['media-ctl','v4l2-ctl']:
 p=subprocess.run([name,'--version'],capture_output=True,text=True,timeout=10);versions[name]=(p.stdout+p.stderr).strip()
r=dict(stage=197,new_packages=['v4l-utils=1.32.0-r1','v4l-utils-libs=1.32.0-r1'],existing_packages_upgraded=False,modemmanager191_unchanged=True,tools=versions);(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
