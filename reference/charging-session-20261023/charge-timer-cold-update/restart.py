"""Original EUD-off cold restart, prepared offline; no carrier write action."""
from pathlib import Path
import argparse,ast,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
adapter=load('timer_cold_restart_adapter',HERE/'host.py');u=adapter.u
m=load('timer_cold_prior_restart_owner',HERE.parent/'protection-profile-update/restart.py')
m.adapter=adapter;m.u=u;m.TX='charging-r7-timer-hold-20261024-01';m.REMOTE=u.REMOTE+'/restart'
def build():
    adapter.check();request=u.request();cohort=json.loads((HERE.parent/'charge-timer-hold-r2-candidate/cohort-result.json').read_bytes())
    previous=json.loads((adapter.PREVIOUS/'request-private.json').read_bytes());source={}
    for name in ['quiesce','restart']:
        text=(adapter.PREVIOUS/'restart-local'/(name+'.py')).read_text()
        if name=='quiesce':
            text=u.replace(text,repr('/root/charging-management-20261023/irq-native-usb-pm-stage-wake-20261024-01/device-stage/result.json'),repr(u.REMOTE+'/device-stage/result.json'))
        else:text=u.replace(text,"meta['token']="+repr(previous['lease_token']),"meta['token']="+repr(request['lease_token']))
        point="assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'"
        extra="\nassert hashlib.sha256(Path('/sys/module/samurai_mp2650/notes/.note.gnu.build-id').read_bytes()).hexdigest()==meta['source_charger_note']"
        text=u.replace(text,point,point+extra);ast.parse(text);source[name]=text.encode()
    meta=dict(schema='samurai-r7-restart-review-v1',transaction_id=m.TX,boot_id=request['identity']['boot_id'],kernel_release='7.3.0-rc6-rmx1931-samurai-k363+',kernel_version=u.VERSION,
        rootfs_release_sha256=request['identity']['rootfs_sha256'],
        disk_pair={'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko':cohort['retained_USB_sha256'],
                   '/usr/share/samurai-charging/manifest.json':cohort['target_manifest_sha256']},
        old_loaded_usb_note_sha256='028ea63c24b0b46ec6edb03b9c3cbfc999c4b7a119034dc18ac70d1bcbf064e6',
        source_charger_note='fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016',
        changed_files={key:value for key,value in json.loads((u.BASE/'charge-timer-hold-cohort-private-02/manifest-new.json').read_bytes())['installed_files'].items() if key.endswith('/samurai-mp2650.ko')},
        source_protection_note='bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd',
        serial_sha256=request['identity']['serial_sha256'],compatible_sha256=request['identity']['compatible_sha256'],
        adoption_guard=request['adoption']['guard_path'],stage_result=u.REMOTE+'/device-stage/result.json')
    meta['changed_files']['/usr/share/samurai-charging/manifest.json']=cohort['target_manifest_sha256']
    return source,meta
m.build=build
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','quiesce','restart']);a=p.parse_args()
    print(json.dumps(getattr(m,a.action)(),indent=2))
