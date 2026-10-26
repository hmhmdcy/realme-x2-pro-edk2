from pathlib import Path
import io,json,shutil,tarfile
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
d=json.loads((host.PRIVATE/'product-r1-observation.json').read_text())
assert d['state']['terminal'] and not d['worker_live'] and d['state']['summary']['passed']
new={r['name']:r['version'] for r in json.loads((host.PRIVATE/'runtime-records.json').read_text())}
proof=dict(stage=321,packages=new,old_packages={name:('0.1.0-r20' if name.startswith('samurai-camera-') else '99990.7.2-r25') for name in new},
 module_note_sha256='6ebc03a5c7a1f908252a392fdc8cf2835a78d97adf4972e575ff987ccb0a4863',module_stage=318,module_unchanged=True)
(host.PRIVATE/'install-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
s=(HERE.parent/'kernel316/native-install.py').read_text().replace('stage=316','stage=321').replace("'stage':316","'stage':321").replace('0.1.0-r20','0.1.0-r21')
a=s.index(" target=Path(subprocess.check_output");b=s.index(' consumers=services()',a)
s=s[:a]+" if sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')!=proof['module_note_sha256']:raise RuntimeError('CAMSS baseline changed')\n"+s[b:]
s=s.replace(" shutil.copyfile(target,root/'qcom-camss-before.ko')\n",'')
s=s.replace(" run(['rmmod','qcom_camss'],'unload');changed=True\n",'')
a=s.index(" save('installing-module')");b=s.index(" if sha('/sys/module",a);s=s[:a]+s[b:]
s=s.replace("   if changed and Path('/sys/module/qcom_camss').exists():run(['rmmod','qcom_camss'],'rollback-unload')\n",'')
a=s.index('   if target:replace_module');b=s.index('   for name in ',a);s=s[:a]+s[b:]
s=s.replace('packages=versions(),','packages=versions(),module_unchanged=True,kernel_image_unchanged=True,')
(HERE/'native-install.py').write_text(s)
files={'worker.py':HERE/'native-install.py','proof.json':host.PRIVATE/'install-proof.json','pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe','bin/pw-hardware-probe':SDK/'private/camss316-runtime/pw-hardware-probe'}
with tarfile.open(host.PRIVATE/'install.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(raw))
 for p in (host.PRIVATE/'runtime-repository').rglob('*'):tar.add(p,arcname='repository/'+p.relative_to(host.PRIVATE/'runtime-repository').as_posix(),recursive=False)
for name in ['launch-install.py','inspect-install.py']:
 s=(HERE.parent/'kernel316'/name).read_text().replace('k316-install-','k321-install-').replace('stage=316','stage=321')
 (HERE/name).write_text(s)
print('Prepared r26/r21 package transaction with r25/r20 rollback; CAMSS318 retained.')
