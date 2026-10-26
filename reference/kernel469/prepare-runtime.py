"""Prepare a mode2 window from the tested 467 wrapper, adding sensor restoration."""
from pathlib import Path
import hashlib,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
path=HERE.parent/'kernel467/prepare-runtime.py';raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='10230ef420468e78c20f602de498083146c541075482916c496c3c156029b9d5'
attempt='r1'
if '--attempt' in sys.argv:
    index=sys.argv.index('--attempt');attempt=sys.argv[index+1];del sys.argv[index:index+2]
assert attempt in ['r1','r2']
source=raw.decode().replace('kernel467','kernel469').replace('k467-tele-','k469-tele-ltm-').replace('stage=467','stage=469')
if attempt=='r2':
    source=source.replace('k469-tele-ltm-r1','k469-tele-ltm-r2').replace("private/'prepared-r1'","private/'prepared-r2'")
    source=source.replace('prepared-validation-private.json','prepared-r2-validation-private.json')
def replace(a,b):
    global source
    assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
replace("private.parent/'kernel440/factory-s5k3m5-private.yaml'","private/'factory-s5k3m5-mode2-private.yaml'")
source=source.replace('41cba861b491d583c685e07fdc0e97d635f8922f7132abefa15d0632d4fab0a4','6396ced1039e352a14c7a07187e780596a3a4180b22391bca0b30f7518db4094')
replace("proof=dict(modules=module_proof,boot_guard=handoff['boot_guard_path'])",'''sensor=private/'s5k3m5-mode2-build2.ko'
sensor_build=json.loads((HERE/'module-build-validation.json').read_bytes())
sensor_controls=json.loads((HERE/'format-control-validation.json').read_bytes())
assert sensor_build['passed'] and sensor_controls['passed']
assert sensor_controls['candidate_sha256']==sensor_build['candidate_sha256']
assert sha(sensor)==sensor_build['module_sha256']
raw=sensor.read_bytes();shoff=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',raw,shoff+i*stride) for i in range(count)]
names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
note=next(section for section in sections if names[section[0]:].split(bytes([0]))[0]==b'.note.gnu.build-id')
files['s5k3m5-mode2.ko']=sensor
proof=dict(modules=module_proof,boot_guard=handoff['boot_guard_path'],sensor=dict(file='s5k3m5-mode2.ko',
    sha256=sha(sensor),note_sha256=hashlib.sha256(raw[note[4]:note[4]+note[5]]).hexdigest()))''')
replace("model='s5k3m5',sensor_mode=3,actual_sensor=[2104,1560],original440_profile_preserved=True,", "model='s5k3m5',sensor_mode=2,actual_sensor=[4208,2368],original440_mode3_preserved=True,candidate_sensor_module=True,")
replace("files['capture-body-tele.py']=HERE/'capture-body-tele.py'", "files['capture-body-tele.py']=HERE/'capture-body-tele.py'\nfiles['capture-body-base.py']=reference/'kernel467/capture-body-tele.py'")
needle="worker=prefix+body;ast.parse(worker);assert 'os.killpg' not in worker"
extra='''# The CAMSS notifier is removed first, so no sensor devnode survives the
# controlled sensor replacement. Leave the original module file untouched.
body=body.replace("names=['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']", "names=['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']\\nsensor_changed=False")
needle=" items=services();"
assert body.count(needle)==1
sensor_check=""" tele_formal=baseline['tele_sensor']
 assert hashlib.sha256(Path(tele_formal['path']).read_bytes()).hexdigest()==tele_formal['sha256']
 assert hashlib.sha256(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()).hexdigest()==tele_formal['note_sha256']
 state['sensor_formal_before']=tele_formal
"""
body=body.replace(needle,sensor_check+needle)
needle=" assert not (dev/'driver').exists()"
assert body.count(needle)==1
body=body.replace(needle,needle+"""
 run(['rmmod','s5k3m5'],'remove-sensor');sensor_changed=True
 run(['insmod',str(root/proof['sensor']['file'])],'load-sensor')
 assert hashlib.sha256(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()).hexdigest()==proof['sensor']['note_sha256']
 state['candidate_sensor_note']=proof['sensor']['note_sha256']
""")
needle="   run(['modprobe','qcom_camss'],'restore-formal');"
assert body.count(needle)==1
body=body.replace(needle,"""   if sensor_changed:
    if Path('/sys/module/s5k3m5').exists():run(['rmmod','s5k3m5'],'cleanup-sensor')
    run(['modprobe','s5k3m5'],'restore-sensor')
    assert hashlib.sha256(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()).hexdigest()==baseline['tele_sensor']['note_sha256']
    state['sensor_module_restored']=True
"""+needle)
needle="  state['tele_final_checks']=tele['finalize'](root,state)"
assert body.count(needle)==1
body=body.replace(needle,needle+"""
  assert state.get('sensor_module_restored')
  assert hashlib.sha256(Path(baseline['tele_sensor']['path']).read_bytes()).hexdigest()==baseline['tele_sensor']['sha256']
""")
'''
replace(needle,extra+needle)
source=source.replace("private/'factory-s5k3m5-mode2-private.yaml'","private.parent/'kernel468/factory-s5k3m5-mode2-private.yaml'")
source=source.replace("private/'s5k3m5-mode2-build2.ko'","private.parent/'kernel468/s5k3m5-mode2-build2.ko'")
source=source.replace("HERE/'module-build-validation.json'","reference/'kernel468/module-build-validation.json'")
source=source.replace("HERE/'format-control-validation.json'","reference/'kernel468/format-control-validation.json'")
source=source.replace("cases=['1280x720-isolated','1920x1080-isolated']","cases=['1280x720-isolated']")
source=source.replace("modules=json.loads", "files['pd10-ipe']=private.parent/'kernel441/pd10-ipe'\nassert sha(files['pd10-ipe'])=='5be7faeb481c68996e57f476889f5e51d1af550922d0c0ba809b6b5c5daac5f2'\nmodules=json.loads",1)
exec(compile(source,str(path)+'-mode2-increment','exec'))
