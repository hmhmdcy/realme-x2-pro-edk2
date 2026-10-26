from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
proof=json.loads((here/'default-cpu-capture-validation.json').read_text());assert not proof['system_configuration_opened'] and proof['taint']==0
code=r'''
from pathlib import Path
import hashlib,json,os,stat
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k212-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k212-config-directory-fix';out.mkdir(mode=0o700)
directory=Path('/etc/libcamera');assert directory.is_dir() and not directory.is_symlink() and directory.stat().st_uid==0
assert sorted(p.name for p in directory.iterdir())==['configuration.yaml']
target=directory/'configuration.yaml';assert hashlib.sha256(target.read_bytes()).hexdigest()=='771c516f85cb3c408e42a561beaa4a4bd56f2db9890c81d40e28468205ecc12e'
before=stat.S_IMODE(directory.stat().st_mode);assert before==0o700
os.chmod(directory,0o755);assert stat.S_IMODE(directory.stat().st_mode)==0o755 and stat.S_IMODE(target.stat().st_mode)==0o644
report=dict(stage=212,configuration_directory_before_mode=oct(before),configuration_directory_after_mode='0o755',configuration_file_mode='0o644',configuration_contents_preserved=True,first_capture_failure_preserved=True,no_camera_stream_or_reboot=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);report=json.loads(p.stdout);(here/'config-directory-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
