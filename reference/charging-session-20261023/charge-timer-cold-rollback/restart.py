"""Normal restart after exact inverse staging; offline templates by default."""
from pathlib import Path
import argparse,ast,base64,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=load('timer_inverse_restart_host',HERE/'host.py');u=h.u
prior=load('timer_inverse_original_restart',HERE.parent/'protection-profile-update/restart.py')
prior.u=u;prior.TX='charging-r7-timer-restore-20261024-01';prior.REMOTE=u.REMOTE+'/restart'
def sources():
    root=u.BASE/'charge-timer-cold-update-live-20261024-01'
    previous=json.loads((root/'request-private.json').read_bytes());values={}
    old="sr=json.loads(raw);assert sr['staged'] and sr['terminal'] and sr['stop_verified'] and sr['disk_state']=='all_new_fsynced' and not sr['primary_error'] and not sr['recovery_error']"
    new="sr=json.loads(raw);assert sr['restored'] and sr['terminal'] and sr['stop_verified'] and sr['disk_state']=='all_original_fsynced' and sr['primary_error'] is None and not sr['unknown_write_state'] and not sr['module_or_carrier_action'] and not sr['automatic_replay_or_rollback']"
    for name in ['quiesce','restart']:
        source=(root/'restart-local'/(name+'.py')).read_text();source=u.replace(source,old,new)
        if name=='quiesce':source=u.replace(source,repr('/root/charging-management-20261023/'+previous['transaction_id']+'/device-stage/result.json'),repr(u.REMOTE+'/device-rollback/result.json'))
        else:source=u.replace(source,"meta['token']="+repr(previous['lease_token']),"meta['token']=meta['restart_token']")
        ast.parse(source);values[name]=source.encode()
    return values
def build():
    request=h.request();m=h.worker();rows=list(u.OUT.glob('raw-*/device-rollback/result.json'));assert len(rows)==1
    raw=rows[0].read_bytes();result=json.loads(raw);terminal=json.loads((rows[0].parent.parent/'worker-terminal-private.json').read_bytes())
    assert terminal['terminal'] and terminal['returncode']==0 and terminal['receipt_error'] is None
    assert result['restored'] and result['terminal'] and result['disk_state']=='all_original_fsynced' and result['stop_verified'] and result['primary_error'] is None
    notes=m.expected_profile(request)['notes'];assert result['actual_resident_notes']==notes
    guard=u.REMOTE+'/restart/boot-id-private.txt'
    meta=dict(schema='samurai-r7-restart-review-v1',transaction_id=prior.TX,boot_id=request['identity']['boot_id'],kernel_release=m.RELEASE,kernel_version=m.VERSION504,
        rootfs_release_sha256=request['identity']['rootfs_sha256'],disk_pair={
            '/lib/modules/'+m.RELEASE+'/extra/samurai-charging/samurai-usb-input.ko':'13f41e7cdbd1825982e2155bfb97e0105227179d1afa8da8a2795ba39f4299a4',m.MANIFEST:m.OLD_FILES[m.MANIFEST]},
        old_loaded_usb_note_sha256=notes['samurai-usb-input'],source_charger_note=notes['samurai-mp2650'],source_protection_note=notes['samurai-gauge-protection'],
        changed_files=m.OLD_FILES,serial_sha256=request['identity']['serial_sha256'],compatible_sha256=request['identity']['compatible_sha256'],
        adoption_guard=guard,stage_result=u.REMOTE+'/device-rollback/result.json',stage_result_sha256=u.sha(raw),restart_token=request['lease_token'])
    return sources(),meta
def local():
    values=sources();out=u.OUT/'restart-source-templates';out.mkdir(mode=0o700)
    for name,raw in values.items():u.create(out/(name+'.py'),raw)
    return dict(prepared=True,source_only=True,identity_not_fabricated=True,phone_accessed=False)
def quiesce():
    values,meta=build()
    packet=dict(root=prior.REMOTE,meta=meta,source={key:base64.b64encode(raw).decode() for key,raw in values.items()},hashes={key:u.sha(raw) for key,raw in values.items()})
    code=('PACKET='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json,os,re,runpy,sys
meta=PACKET['meta'];assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==meta['boot_id']
assert hashlib.sha256(Path(meta['stage_result']).read_bytes()).hexdigest()==meta['stage_result_sha256']
assert hashlib.sha256(Path('/sys/module/samurai_mp2650/notes/.note.gnu.build-id').read_bytes()).hexdigest()==meta['source_charger_note']
for path,digest in meta['changed_files'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
behaviour=Path('/sys/class/power_supply/mp2650-input/charge_behaviour').read_text().strip();active=re.findall(r'\[([^\]]+)\]',behaviour)
assert (active[0] if len(active)==1 else behaviour)=='inhibit-charge'
root=Path(PACKET['root']);assert not root.exists();os.umask(0o077);root.mkdir(mode=0o700)
for name,value in PACKET['source'].items():
 raw=base64.b64decode(value,validate=True);assert hashlib.sha256(raw).hexdigest()==PACKET['hashes'][name]
 with (root/(name+'.py')).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
with (root/'boot-id-private.txt').open('x') as f:f.write(meta['boot_id']+'\n');f.flush();os.fsync(f.fileno())
with (root/'guard.json').open('x') as f:json.dump(meta,f);f.flush();os.fsync(f.fileno())
sys.argv=['quiesce','--guard',str(root/'guard.json'),'--commit-quiesce'];runpy.run_path(str(root/'quiesce.py'),run_name='__main__')
result=Path('/var/lib/samurai')/meta['transaction_id']
print(json.dumps(dict(quiesced=True,state=json.loads((result/'state-private.json').read_bytes()),summary=json.loads((result/'summary.json').read_bytes()))))
'''
    return u.call('quiesce',code,False)
prior.build=build
def restart():return prior.restart()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='local',choices=['local','quiesce','restart']);a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
