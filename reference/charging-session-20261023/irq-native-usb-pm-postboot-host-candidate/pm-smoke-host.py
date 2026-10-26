"""One supervised 15-second PM smoke check on the actually adopted 504 boot."""
from pathlib import Path
import argparse,ast,base64,hashlib,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import host,adopt
PRIMITIVE=HERE.parent/'pm-current-evidence-candidate/pm-transaction.py'
def inputs():
    host.source_check();raw=PRIMITIVE.read_bytes()
    host.need(host.sha(raw)=='fd3fd4bef1e04dc8a29b5240cad8989d700021e353e081c0fcf0b297e4bda0a1','original tested PM primitive changed')
    return raw

def worker_code(request):
    device=(host.DEVICE/'device.py').read_bytes().split(b"\nif __name__=='__main__':",1)
    host.need(len(device)==2,'actual collector delimiter')
    return ('PM_REQUEST='+repr(request)+'\n').encode()+device[0]+b'\n'+inputs()+b'\n'+(HERE/'pm-smoke-worker.inc').read_bytes()

def launch(context,camera,probe,capture):
    value=adopt.descriptor(context,camera,probe,capture)
    host.need(value['profile']=='forward_504','adopted current504 only')
    parent=Path(context).resolve().parent;folder=parent/'pm-adoption-01-private'
    actual=json.loads((folder/'adoption-result-private.json').read_bytes());pointer=(folder/'adoption-pointer-private.json').read_bytes()
    host.need(actual['passed'] is True and actual['pointer']==json.loads(pointer) and
              (adopt.BASE/'boot-adoption-private.json').read_bytes()==pointer and actual['pointer']['guard_path']==value['guard'], 'actual current fresh adoption required')
    tx='pm504-smoke-live-20261024-01';root='/root/charging-management-20261023/'+tx
    out=parent/'pm-smoke-01-private';host.need(not out.exists(),'PM intent exists; observe original only')
    request=dict(schema='samurai-native-pm-smoke-v1',postboot_request=value['postboot_request'],adoption_guard=value['guard'])
    worker=worker_code(request);supervisor=(HERE/'pm-smoke-supervisor.py').read_bytes()
    packet=dict(schema='samurai-native-pm-launch-v1',root=root,boot_id=value['boot'],version=value['version'],
                worker_sha256=host.sha(worker),worker=base64.b64encode(worker).decode(),
                supervisor_sha256=host.sha(supervisor),supervisor=base64.b64encode(supervisor).decode(),
                explicit_scope='one supervised PM transaction; no driver, charge-policy, service or partition writes')
    code=('LAUNCH='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys
assert LAUNCH['schema']=='samurai-native-pm-launch-v1'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==LAUNCH['boot_id']
assert os.uname().version==LAUNCH['version']=='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
root=Path(LAUNCH['root']);assert root==Path('/root/charging-management-20261023/pm504-smoke-live-20261024-01') and not root.exists()
worker=base64.b64decode(LAUNCH['worker'],validate=True);supervisor=base64.b64decode(LAUNCH['supervisor'],validate=True)
assert hashlib.sha256(worker).hexdigest()==LAUNCH['worker_sha256'] and hashlib.sha256(supervisor).hexdigest()==LAUNCH['supervisor_sha256']
os.umask(0o077);root.mkdir(mode=0o700)
def save(name,raw):
 with (root/name).open('xb') as file:file.write(raw);file.flush();os.fsync(file.fileno())
save('worker.py',worker);save('supervisor.py',supervisor)
save('launch-private.json',(json.dumps({k:v for k,v in LAUNCH.items() if k not in ('worker','supervisor')},indent=2)+'\n').encode())
with (root/'supervisor-stdout-private.txt').open('xb') as out,(root/'supervisor-stderr-private.txt').open('xb') as err:
 child=subprocess.Popen([sys.executable,'-B',str(root/'supervisor.py'),'--supervise',str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,start_new_session=True)
 stat=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
 receipt=dict(pid=child.pid,startticks=int(stat[19]),argv=[p.decode() for p in Path('/proc',str(child.pid),'cmdline').read_bytes().split(bytes([0])) if p])
 save('supervisor-launch-private.json',(json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(dict(launched=True,worker_result_pending=True,supervisor=receipt,worker_sha256=LAUNCH['worker_sha256'])),flush=True)
'''
    ast.parse(worker);ast.parse(supervisor);ast.parse(code)
    os.umask(0o077);out.mkdir(mode=0o700)
    adopt.save(out/'request-private.json',request);adopt.create(out/'executed-launch-source.py',code)
    reply=adopt.transfer(out,code,host,host.PEER);adopt.save(out/'launch-result-private.json',reply)
    return dict(launched=reply['launched'],worker_result_pending=True,private_directory=str(out))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute',action='store_true')
    for name in ('context','camera','probe-directory','capture-directory'):p.add_argument('--'+name)
    a=p.parse_args();inputs()
    result=launch(a.context,a.camera,a.probe_directory,a.capture_directory) if a.execute else dict(source_only=True,device_accessed=False)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
