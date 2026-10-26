"""Prepare a concrete signed transaction only after packaged consumer tests."""
from pathlib import Path
import hashlib,io,json,subprocess,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
consumer_runs=sys.argv[1:] or ['r3','r5']
consumer_reports=[json.loads((HERE/('consumer-'+run+'-validation.json')).read_text()) for run in consumer_runs]
assert all(report['passed'] for report in consumer_reports)
covered={label for report in consumer_reports for label,item in report['selections'].items() if item['passed']}
assert {model+'-640x480' for model in ['s5kgw1','imx471','imx319','s5k3m5']} <= covered
assert {model+'-raw' for model in ['s5kgw1','imx471','imx319','s5k3m5']} <= covered
assert {'s5kgw1-1920x1080','imx471-1280x720'} <= covered
context=json.loads((host.PRIVATE/'device-context.json').read_text())
records=json.loads((host.PRIVATE/'runtime-records.json').read_text())
new={r['name']:r['version'] for r in records}
assert context['packages']=={name:('0.1.0-r19' if name.startswith('samurai-camera-') else '99990.7.2-r24') for name in new}
kernel=json.loads((HERE.parent/'kernel314/kernel-build-validation.json').read_text());module=Path(kernel['module'])
note=host.PRIVATE/'candidate-module-build-note.bin'
subprocess.run(['aarch64-linux-gnu-objcopy','--dump-section','.note.gnu.build-id='+str(note),str(module),str(host.PRIVATE/'module-note-copy.ko')],check=True)
proof=dict(stage=316,packages=new,old_packages=context['packages'],module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),module_note_sha256=hashlib.sha256(note.read_bytes()).hexdigest(),
 old_module_sha256='09eaf871562f79431009df0b6f3adda026b2da9cd57a1d76dfdf3b284d123eae',kernel_stage=314,consumer_runs=consumer_runs)
(host.PRIVATE/'install-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
files={'worker.py':HERE/'native-install.py','proof.json':host.PRIVATE/'install-proof.json','qcom-camss.ko':module,
 'pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe',
 'bin/pw-hardware-probe':SDK/'private/camss316-runtime/pw-hardware-probe'}
with tarfile.open(host.PRIVATE/'install.tar.gz','w:gz') as tar:
 for name,p in files.items():
  data=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o700 if name=='pipeline-fixture' or name.startswith('bin/') else 0o600
  tar.addfile(item,io.BytesIO(data))
 for p in sorted((host.PRIVATE/'runtime-repository').rglob('*')):
  tar.add(p,arcname='repository/'+p.relative_to(host.PRIVATE/'runtime-repository').as_posix(),recursive=False)
print('Prepared r25/r20 packages plus tested314 module, offline rollback and installed consumer checks.')
