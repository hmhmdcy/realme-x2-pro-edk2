"""Install only the already tested CAMSS module, retaining module rollback."""
from pathlib import Path
import io,json,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
for name in ['hardware-statistics-validation.json','awb-grid-validation.json','probe-r1-validation.json','probe-r2-validation.json']:assert json.loads((HERE/name).read_text())['passed']
source=json.loads((HERE/'source-state.json').read_text());assert source['tracked_clean'] and source['temporary_four_sensor_hardware_tested']
module=Path(json.loads((HERE/'kernel-build-validation.json').read_text())['module'])
proof=json.loads((P/'proof.json').read_text());proof.update(stage=338,old_module_sha256='2f8a94f5bd34694d52a0ff262f7df668d5cbea46a2109fa5b195d510f50547fa',
 old_module_note_sha256='6ebc03a5c7a1f908252a392fdc8cf2835a78d97adf4972e575ff987ccb0a4863')
(P/'install-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
s=(HERE.parent/'kernel318/native-install.py').read_text().replace('stage=318','stage=338').replace("'stage':318","'stage':338").replace('.k318-tmp','.k338-tmp')
needle=" consumers=services();wait_idle()"
s=s.replace(needle," if sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')!=proof['old_module_note_sha256']:raise RuntimeError('Loaded baseline changed')\n"+needle)
s=s.replace(" report['services']={name:"," report['module_path']=str(target)\n report['module_sha256']=sha(target) if target else None\n report['rails']={(p/'name').read_text().strip():{'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())} for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}\n report['services']={name:")
s=s.replace(" and all(len(value)==1 for value in report['services'].values())"," and all(len(value)==1 for value in report['services'].values()) and all(value=={'state':'disabled','users':0} for value in report['rails'].values())")
(HERE/'native-install.py').write_text(s)
files={'worker.py':HERE/'native-install.py','proof.json':P/'install-proof.json','qcom-camss.ko':module,'pipeline-fixture':P.parent/'kernel313/pipeline-fixture',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe','bin/pw-hardware-probe':SDK/'private/camss316-runtime/pw-hardware-probe'}
with tarfile.open(P/'install.tar.gz','w:gz') as tar:
 for name,path in files.items():
  data=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(data))
for name in ['launch-install.py','inspect-install.py']:
 text=(HERE.parent/'kernel318'/name).read_text().replace('k318-install-','k338-install-').replace('stage=318','stage=338');(HERE/name).write_text(text)
print('Prepared tested CAMSS-only installation with an on-device module rollback.')
