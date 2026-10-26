from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k197-offline-tools';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k197-baseline/boot-id-private.txt').read_bytes()
assert not subprocess.run(['pgrep','-x','apk'],capture_output=True).stdout
for r in json.loads((out/'manifest.json').read_text()):assert hashlib.sha256((out/r['file']).read_bytes()).hexdigest()==r['sha256']
before=hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest();assert before=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
args=['apk','add','--no-network',str(out/'v4l-utils-libs-1.32.0-r1.apk'),str(out/'v4l-utils-1.32.0-r1.apk')]
p=subprocess.run(args[:2]+['--simulate']+args[2:],capture_output=True,text=True,timeout=20);(out/'simulate-private.txt').write_text(p.stdout+p.stderr);assert p.returncode==0 and 'Upgrading ' not in p.stdout and 'Removing ' not in p.stdout
p=subprocess.run(args,capture_output=True,text=True,timeout=40);(out/'install-private.txt').write_text(p.stdout+p.stderr);assert p.returncode==0 and hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()==before
assert shutil.which('media-ctl') and shutil.which('v4l2-ctl');tool=out/'front-capture-aarch64-private';tool.chmod(0o700);p=subprocess.run([str(tool),'--self-test'],capture_output=True,text=True,timeout=10);assert p.returncode==0 and 'FRONT_CAPTURE_HASH_SELF_TEST_PASS' in p.stdout
r=dict(stage=197,signature_verification_enforced=True,no_network_install=True,only_two_new_packages=True,modemmanager191_unchanged=True,static_capture_native_self_test_passed=True);(out/'install-summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
