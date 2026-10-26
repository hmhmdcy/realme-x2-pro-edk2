from pathlib import Path
import ast,hashlib,host,json,shutil,urllib.request
here=Path(__file__).resolve().parent;private=host.PRIVATE;private.mkdir(mode=0o700)
shutil.copyfile(private.parent/'kernel214/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k215-baseline';assert not base.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k214-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and os.uname().version.startswith('#183 ')
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
assert json.loads((root/'k214-package-transaction/transaction-state-private.json').read_text())['state']=='verified'
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()=='a28dd67a03afa9e918f87b85030f0158edecbcc2e3f1ce0a36405b78be70ba6a'
base.mkdir(mode=0o700);(base/'boot-id-private.txt').write_bytes(boot);shutil.copyfile(module,base/'imx471-original.ko')
db=Path('/lib/apk/db/installed').read_bytes();assert db==(root/'k214-package-transaction/installed-after-private.txt').read_bytes();(base/'installed-before-private.txt').write_bytes(db)
report=dict(stage=215,fresh_same214_boot_verified=True,current_r5_database_unchanged=True,original_imx471_module_backed_up=True,camera_suspended=True,taint=0,kernel183=True)
(base/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45);(private/'baseline-host-private.log').write_bytes(p.stdout+p.stderr);result=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');source=kernel/'drivers/media/i2c/imx471.c';assert hashlib.sha256(source.read_bytes()).hexdigest()=='c9c4a751521502599ffe0de46bfacc00b9c29237320ee3a7a13d977cc70e8417'
shutil.copyfile(source,private/'imx471-before.c')
print(json.dumps(dict(driver_test_pattern_lines=[line.strip() for line in source.read_text().splitlines() if 'TEST_PATTERN' in line])))
def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'samurai-linux-port-source-research'})
    with urllib.request.urlopen(request,timeout=30) as response:return response.read()
commit=json.loads(fetch('https://api.github.com/repos/cschalle/mipi-fixes-x1-aura/commits?per_page=1'))[0]['sha']
tree=json.loads(fetch('https://api.github.com/repos/cschalle/mipi-fixes-x1-aura/git/trees/'+commit+'?recursive=1'))['tree']
files=[item['path'] for item in tree if item['type']=='blob' and (item['path'].endswith('.patch') or item['path'].lower() in ['readme.md','license'])]
(private/'related-upstream-source-list-private.json').write_text(json.dumps(dict(repository='https://github.com/cschalle/mipi-fixes-x1-aura',commit=commit,paths=files),indent=2)+'\n')
destination=private/'related-upstream';destination.mkdir(mode=0o700)
for name in files:
    assert '..' not in Path(name).parts and not name.startswith('/');target=destination/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(fetch('https://raw.githubusercontent.com/cschalle/mipi-fixes-x1-aura/'+commit+'/'+name))
print(json.dumps(dict(primary_repository_commit=commit,source_files=files)))
