"""Prepare final read-only health checks, retaining historical phase223 receipts."""
from pathlib import Path

here = Path(__file__).resolve().parent
source = (here.parent / 'kernel223/final-health.py').read_text()
source = source.replace('k223-final-health', 'k224-final-health').replace('k223-baseline', 'k224-baseline')
source = source.replace('k223-r8-package-candidates', 'k224-r11-package-candidates')
source = source.replace('k223-full-mode-experiment', 'k224-full-mode-experiment')
start = source.index('trials=[]\n')
end = source.index('import struct,fcntl,re\n', start)
source = source[:start] + """assert json.loads((root/'k224-r11-package-transaction/transaction-state-private.json').read_text())['state']=='verified'
assert json.loads((root/'k224-r11-package-transaction/policy-reload-state-private.json').read_text())['state']=='verified'
assert json.loads((root/'k224-full-mode-experiment/state-private.json').read_text())['state']=='finished-default-mode-restored'
""" + source[end:]
marker = 'r=dict(stage=223,'
assert source.count(marker) == 1
extra = """
def records(data):
 result={}
 for block in data.decode().split('\\n\\n'):
  names=[l[2:] for l in block.splitlines() if l.startswith('P:')]
  if names:result[names[0]]=block
 return result
old=records((root/'k224-r11-package-transaction/installed-before-private.txt').read_bytes())
new=records(Path('/lib/apk/db/installed').read_bytes());package_names={p['name'] for p in manifest['packages']}
assert len(new)==944 and set(old)==set(new)
assert all(new[name]==block for name,block in old.items() if name not in package_names)
assert all('V:'+package['version'] in new[package['name']].splitlines() for package in manifest['packages'])
assert Path('/etc/apk/world').read_bytes()==(root/'k224-r11-package-transaction/world-before-private.txt').read_bytes().replace(b'samurai-camera-stack=0.1.0-r3',b'samurai-camera-stack=0.1.0-r6')
assert Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text()=='ndx file:///var/lib/samurai/k224-r11-package-candidates/forward/packages.adb\\n'
assert b'dma_heap: system' in Path('/etc/libcamera/configuration.yaml').read_bytes()
assert not any(Path('/etc/libcamera').glob('*.apk-new'))
import grp
for name in ['system','default_cma_region','reserved']:
 p=Path('/dev/dma_heap')/name
 assert p.stat().st_uid==0 and p.stat().st_gid==grp.getgrnam('video').gr_gid and stat.S_IMODE(p.stat().st_mode)==0o660
p=Path('/dev/dma_heap/fastrpc-shared-pool');assert p.stat().st_uid==0 and p.stat().st_gid==0 and stat.S_IMODE(p.stat().st_mode)==0o600
assert len(list((Path('/usr/lib/modules')/os.uname().release).rglob('*.ko')))==772
def module_note(path):
 data=path.read_bytes();offset=struct.unpack_from('<Q',data,40)[0];size,count,strings=struct.unpack_from('<HHH',data,58)
 hs=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)];s=hs[strings];names=data[s[4]:s[4]+s[5]]
 values=[data[h[4]:h[4]+h[5]] for h in hs if names[h[0]:].split(b'\\0',1)[0]==b'.note.gnu.build-id']
 assert len(values)==1
 return values[0]
assert module_note(module)==Path('/sys/module/imx471/notes/.note.gnu.build-id').read_bytes()
policies=[]
for process in Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  if (process/'comm').read_text().strip()=='wireplumber' and int((process/'status').read_text().split('Uid:',1)[1].split()[0])==10000:policies.append(process)
 except OSError:pass
assert len(policies)==1
policy=policies[0];maps=(policy/'maps').read_text();(out/'policy-current-maps-private.txt').write_text(maps)
paths=sorted({line.split()[-1] for line in maps.splitlines() if '/usr/lib/libcamera' in line})
assert paths and '(deleted)' not in '\\n'.join(line for line in maps.splitlines() if '/usr/lib/libcamera' in line)
expected={name:item['sha256'] for package in manifest['packages'] for name,item in package['files'].items() if item['kind']=='file'}
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected[name.lstrip('/')] for name in paths)
env={k.decode():v.decode() for item in (policy/'environ').read_bytes().split(b'\\0') if b'=' in item for k,v in [item.split(b'=',1)]}
assert not any(k in env for k in ['LD_LIBRARY_PATH','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_IPA_CONFIG_PATH'])
"""
source = source.replace(marker, extra + 'r=dict(stage=224,')
source = source.replace('r8_r3_camera_payload_records_verified', 'r11_r6_camera_payload_records_verified')
source = source.replace('temporary_camss_trials_restored=len(trials),', '')
source = source.replace('camera_metadata_captures_performed=True,', 'camera_metadata_captures_performed=True,installed_package_count=944,unrelated_package_records_preserved=937,loaded_sensor_module_note_verified=True,current_policy_r11_library_hashes_verified=True,general_dma_heaps_video0660_and_dsp_private0600=True,')
compile(source, 'final-health.py', 'exec')
(here / 'final-health.py').write_text(source)

source = (here.parent / 'kernel223/collect-final-evidence.py').read_text().replace('223', '224')
source = source.replace('original_camss_backup_in_this_archive=True,', 'all_three_candidates_and_native_failures_retained=True,')
compile(source, 'collect-final-evidence.py', 'exec')
(here / 'collect-final-evidence.py').write_text(source)
print('Final health and private evidence collectors prepared; no native action performed.')
