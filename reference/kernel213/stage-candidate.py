from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent;assert sys.argv[1:] in [['helper'],['lut']];variant=sys.argv[1]
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
variant=VARIANT;out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';build=out/'build';prefix=Path('/run/samurai-camera213-'+variant);assert not prefix.exists()
proof=json.loads((out/('helper-build-summary.json' if variant=='helper' else 'lut-build-summary.json')).read_text())
assert proof['installed_camera_products_unchanged']
db=Path('/lib/apk/db/installed').read_bytes();original=json.loads((root/'k213-baseline/products-before-private.json').read_text())
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest for name,digest in original.items())
env=json.loads((out/'build-environment-private.json').read_text());prefix.mkdir(mode=0o755)
def installer_umask():os.umask(0o022)
with (out/(variant+'-candidate-install-private.log')).open('wb') as log:
    subprocess.run([str(sdk/'usr/bin/meson'),'install','-C',str(build),'--destdir',str(prefix),'--no-rebuild'],env=env,preexec_fn=installer_umask,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert not any(p.is_file() and ('priv-key' in p.name or p.suffix=='.pem') for p in prefix.rglob('*'))
for p in [prefix,*prefix.rglob('*')]:
    if p.is_dir() and not p.is_symlink():p.chmod(0o755)
products={}
for relative in ['usr/bin/cam','usr/lib/libcamera.so.0.7.2','usr/lib/libcamera-base.so.0.7.2','usr/lib/libcamera/ipa/ipa_soft_simple.so','usr/lib/libcamera/ipa/ipa_soft_simple.so.sign','usr/libexec/libcamera/soft_ipa_proxy']:
    p=prefix/relative;assert p.is_file(),relative
    if not p.is_symlink():p.chmod(0o755 if relative.endswith(('/cam','/soft_ipa_proxy')) or '.so' in p.name and not p.name.endswith('.sign') else 0o644)
    products[relative]=hashlib.sha256(p.read_bytes()).hexdigest()
assert '#define HAVE_DEBAYER_EGL 1' in (build/'config.h').read_text()
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest for name,digest in original.items()) and db==Path('/lib/apk/db/installed').read_bytes()
record=dict(stage=213,variant=variant,isolated_candidate_staged=True,private_signing_key_not_staged=True,gpu_isp_compiled=True,installed_camera_products_unchanged=True,package_database_unchanged=True,products=products)
(out/(variant+'-candidate-summary.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
'''.replace('VARIANT',repr(variant))
p=host.ssh('python3 -',input=code.encode(),timeout=180);(host.PRIVATE/(variant+'-candidate-stage-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/(variant+'-candidate-staging-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
