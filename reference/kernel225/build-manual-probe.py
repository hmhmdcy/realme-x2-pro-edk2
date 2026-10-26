from pathlib import Path
import gzip,hashlib,host,json,shlex,shutil,subprocess

here=Path(__file__).resolve().parent;private=host.PRIVATE;sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((here/'host-runtime-qa-validation.json').read_text())['all_five_ipa_signatures_valid']
source=sdk/'private/manual-control-probe225.cpp';assert not source.exists();shutil.copyfile(here/'manual-control-probe.cpp',source)
args=['chroot',str(sdk),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread',
 '-I/candidate225/usr/include/libcamera','/private/manual-control-probe225.cpp','-L/candidate225/usr/lib',
 '-Wl,-rpath-link,/candidate225/usr/lib','-lcamera','-lcamera-base','-o','/private/manual-control-probe225']
p=subprocess.run(args,capture_output=True,timeout=180);(private/'manual-probe-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
target=private/'manual-control-probe';assert not target.exists();shutil.copyfile(sdk/'private/manual-control-probe225',target)
data=target.read_bytes();digest=hashlib.sha256(data).hexdigest();payload=gzip.compress(data,mtime=0);assert len(payload)<65536
code="from pathlib import Path;import gzip,hashlib,sys;root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k225-baseline/boot-id-private.txt').read_bytes();p=Path('/run/samurai-camera225-probes/manual-control-probe');assert not p.exists();p.parent.mkdir(mode=0o755,exist_ok=True);d=gzip.decompress(sys.stdin.buffer.read());assert hashlib.sha256(d).hexdigest()=="+repr(digest)+";p.write_bytes(d);p.chmod(0o755)"
host.ssh('python3 -c '+shlex.quote(code),input=payload,timeout=30)
r=dict(stage=225,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=digest,bytes=len(data),
 public_api_only=True,no_client_pixels_mapped_or_scene_saved=True,probe_uploaded_with_hash_verification=True,
 nine_transition_phases_and_restart=True,physical_tests_not_yet_run=True)
(here/'manual-probe-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
