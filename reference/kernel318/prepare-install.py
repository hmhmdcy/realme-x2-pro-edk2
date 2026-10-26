"""Prepare only the tested CAMSS module; retain current packages and Image."""
from pathlib import Path
import hashlib,io,json,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((HERE/'pattern-r6-image-validation.json').read_text())['passed']
covered=set()
for run in ['r4','r5']:
 d=json.loads((host.PRIVATE/('probe-'+run+'-observation.json')).read_text())
 r=d['state']['summary'];assert d['state']['terminal'] and not d['worker_live'] and r['deployment_restored'] and not any(r['fault_delta'].values())
 covered.update(m for m,c in r['captures'].items() if c['probe_passed'] and c['cleanup_restored'])
assert {'s5kgw1','imx471','imx319','s5k3m5'}<=covered
s=(HERE.parent/'kernel316/native-install.py').read_text().replace('stage=316','stage=318').replace("'stage':316","'stage':318").replace('.k316-tmp','.k318-tmp')
a=s.index('def versions():');b=s.index('def replace_module',a);s=s[:a]+s[b:]
s=s.replace(" if versions()!=proof['old_packages']:raise RuntimeError('Installed package baseline changed')\n",'')
a=s.index(" backup=root/'backup';backup.mkdir()");b=s.index(" shutil.copyfile(target,root/'qcom-camss-before.ko')",a);s=s[:a]+s[b:]
a=s.index(" for kind in ['forward','rollback']:");b=s.index(" save('stopping-consumers')",a);s=s[:a]+s[b:]
a=s.index(" save('installing-packages')");b=s.index(" save('installing-module')",a);s=s[:a]+s[b:]
s=s.replace(" Path('/etc/apk/repositories.d/60-samurai-camera.list').write_text('ndx file://'+str(root/'repository/forward/packages.adb')+'\\n')\n",'')
a=s.index('   if packages_sent:');b=s.index('   if target:replace_module',a);s=s[:a]+s[b:]
s=s.replace("   for name in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']:shutil.copyfile(root/'backup'/name,Path('/')/name)\n",'')
s=s.replace(',packages=versions()',',packages_unchanged=True,kernel_image_unchanged=True')
(HERE/'native-install.py').write_text(s)
module=Path(json.loads((HERE/'kernel-build-validation.json').read_text())['module'])
note=host.PRIVATE/'candidate-module-build-note.bin'
subprocess.run(['aarch64-linux-gnu-objcopy','--dump-section','.note.gnu.build-id='+str(note),str(module),str(host.PRIVATE/'module-note-copy.ko')],check=True)
proof=dict(stage=318,module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),module_note_sha256=hashlib.sha256(note.read_bytes()).hexdigest(),old_module_sha256='39a420145981206afe324015c6cf7cafe92aa1fae44d68b7efbffd5d4b23c730')
(host.PRIVATE/'install-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
files={'worker.py':HERE/'native-install.py','proof.json':host.PRIVATE/'install-proof.json','qcom-camss.ko':module,
 'pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe',
 'bin/pw-hardware-probe':SDK/'private/camss316-runtime/pw-hardware-probe'}
with tarfile.open(host.PRIVATE/'install.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600
  tar.addfile(item,io.BytesIO(raw))
for name in ['launch-install.py','inspect-install.py']:
 t=(HERE.parent/'kernel316'/name).read_text().replace('k316-install-','k318-install-').replace('stage=316','stage=318')
 (HERE/name).write_text(t)
print(json.dumps(proof,indent=2))
