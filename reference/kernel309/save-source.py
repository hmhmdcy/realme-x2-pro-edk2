"""Commit only the common receiver-clock fix after native four-camera tests."""
from pathlib import Path
import hashlib,json,struct,subprocess
HERE=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera309-link-kernel')
proof=json.loads((HERE/'capture-validation.json').read_text())
if not proof['four_camera_on_fixed_module'] or not proof['metadata_passed']:raise RuntimeError('Fix is not verified')
names=['drivers/media/platform/qcom/camss/'+n for n in ['camss.c','camss.h','camss-vfe.c']]
base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip()
patch=subprocess.check_output(['git','diff','--',*names],cwd=TREE)
if not patch:raise RuntimeError('Already committed; inspect current source')
(HERE/'receiver-pixel-rate.patch').write_bytes(patch)
subprocess.run(['git','diff','--check'],cwd=TREE,check=True,capture_output=True)
subprocess.run(['git','add','--',*names],cwd=TREE,check=True)
subprocess.run(['git','commit','-m','media: qcom: camss: clock the receiver from CSI-2 link throughput'],cwd=TREE,check=True,capture_output=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip()
module=Path(json.loads((HERE/'kernel-build-validation.json').read_text())['module'])
raw=module.read_bytes()
offset=struct.unpack_from('<Q',raw,40)[0];size,count,strings=struct.unpack_from('<HHH',raw,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*size) for i in range(count)]
names_table=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
note=next(raw[x[4]:x[4]+x[5]] for x in sections if names_table[x[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
report={'stage':309,'tree':str(TREE),'branch':'samurai-link309','base_commit':base,'commit':commit,
 'source_clean':not subprocess.check_output(['git','status','--porcelain'],cwd=TREE),
 'module_sha256':hashlib.sha256(raw).hexdigest(),'module_note_sha256':hashlib.sha256(note).hexdigest(),
 'not_pushed':True,'array_clock_and_sensor_driver_unchanged':True,
 'primary_protocol':'https://www.kernel.org/doc/html/v6.10/driver-api/media/tx-rx.html#pixel-rate'}
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
