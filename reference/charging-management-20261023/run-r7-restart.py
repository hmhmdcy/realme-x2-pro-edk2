"""Activate staged R7 through the established same-image restart path, once."""
from pathlib import Path
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shlex
import subprocess

REF=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=PRIVATE/'r7-restart'
CANDIDATE=REF.parent/'charging-oem-audit-20261023/normal-restart-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

PREPARE=r'''from pathlib import Path
import base64,hashlib,json,os,sys
os.umask(0o077);data=json.loads(sys.stdin.buffer.read())
sha=lambda raw:hashlib.sha256(raw).hexdigest()
stage=Path('/root/charging-management-20261023')/data['stage_transaction']
raw=(stage/'result.json').read_bytes();assert sha(raw)==data['stage_receipt_sha256']
proof=json.loads(raw)
assert proof['staged'] and proof['terminal'] and proof['phase']=='staged'
assert proof['disk_state']=='r7_files_staged' and proof['runtime_pending']
assert proof['stop_verified'] and proof['resident_provider_still_r6']
assert not any(proof.get(k) for k in ['primary_error','stop_error','recovery_error','receipt_error','close_error','unknown_write_state'])
pidmeta=json.loads(stage.with_name(stage.name+'-runner').with_suffix('.pid-private.json').read_text())
proc=Path('/proc')/str(pidmeta['pid'])
if proc.exists():
 argv=(proc/'cmdline').read_bytes().split(bytes([0]))
 assert pidmeta['worker'].encode() not in argv,'stage worker still running'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==data['expected_boot']==Path('/var/lib/samurai/k449-adopted/boot-id-private.txt').read_text().strip()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+' and os.uname().version.startswith('#363 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
pair={name:entry['sha256'] for name,entry in proof['final_files'].items()}
for name,digest in pair.items():
 p=Path(name);assert p.is_file() and not p.is_symlink() and p.stat().st_uid==0
 assert p.stat().st_mode&0o777==0o600 and sha(p.read_bytes())==digest
note=Path('/sys/module/samurai_usb_input/notes/.note.gnu.build-id').read_bytes()
assert sha(note)==proof['resident_usb_note_sha256']
guard={'schema':'samurai-r7-restart-review-v1','transaction_id':data['transaction_id'],
 'boot_id':boot,'kernel_release':os.uname().release,'kernel_version':os.uname().version,
 'rootfs_release_sha256':sha(Path('/etc/samurai-rootfs-release').read_bytes()),
 'disk_pair':pair,'old_loaded_usb_note_sha256':sha(note),
 'stage_receipt_sha256':data['stage_receipt_sha256'],'stage_transaction':data['stage_transaction']}
base=Path('/root/charging-management-20261023')/data['transaction_id']
assert not base.exists() and not (Path('/var/lib/samurai')/data['transaction_id']).exists()
assert not (Path('/run')/(data['transaction_id']+'-reboot-phase-private.json')).exists()
base.mkdir(mode=0o700)
def create(p,raw):
 with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
for name,entry in data['workers'].items():
 raw=base64.b64decode(entry['base64'],validate=True);assert sha(raw)==entry['sha256']
 create(base/name,raw)
create(base/'guard-private.json',json.dumps(guard,indent=2).encode())
print(json.dumps({'guard':guard,'base':str(base),'prepared':True}),flush=True)
'''

QUIESCE=r'''from pathlib import Path
import hashlib,json,os,subprocess,sys
os.umask(0o077);data=json.loads(sys.stdin.buffer.read());base=Path(data['base'])
assert hashlib.sha256((base/'guard-private.json').read_bytes()).hexdigest()==data['guard_sha256']
worker=base/'r7-quiesce-review.py'
assert hashlib.sha256(worker.read_bytes()).hexdigest()==data['worker_sha256']
assert not (base/'quiesce-process-private.json').exists() and not (base/'quiesce.log').exists()
assert not (Path('/var/lib/samurai')/data['transaction_id']).exists()
with (base/'quiesce.log').open('xb') as log:
 child=subprocess.Popen(['python3','-B',str(worker),'--guard',str(base/'guard-private.json'),'--commit-quiesce'],
  stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
receipt={'pid':child.pid,'startticks':ticks,'worker':str(worker),'transaction_id':data['transaction_id']}
with (base/'quiesce-process-private.json').open('x') as f:json.dump(receipt,f);f.flush();os.fsync(f.fileno())
print(json.dumps(receipt),flush=True)
'''

FETCH=r'''from pathlib import Path
import base64,hashlib,json,sys
data=json.loads(sys.stdin.buffer.read());base=Path(data['base'])
p=base/'quiesce-process-private.json';receipt=json.loads(p.read_text()) if p.exists() else None
state='launch_outcome_unknown'
if receipt:
 p=Path('/proc')/str(receipt['pid'])
 try:
  argv=(p/'cmdline').read_bytes().split(bytes([0]));ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]
  state='alive' if ticks==receipt['startticks'] and receipt['worker'].encode() in argv else 'pid_reused'
 except FileNotFoundError:state='absent'
 except OSError:state='unknown'
files={};out=Path('/var/lib/samurai')/data['transaction_id']
if out.exists():
 for p in sorted(out.iterdir()):
  assert p.is_file() and not p.is_symlink() and p.stat().st_size<20000000
  raw=p.read_bytes();files[p.name]={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
print(json.dumps({'process_state':state,'process':receipt,'files':files,
 'log':(base/'quiesce.log').read_text()[-12000:] if (base/'quiesce.log').exists() else None}))
'''


def marker(name,data):
    with (OUT/name).open('x') as f:
        json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
    fd=os.open(OUT,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def main(action,confirmed):
    OUT.mkdir(mode=0o700,exist_ok=True)
    spec=importlib.util.spec_from_file_location('window',REF/'device-window.py')
    window=importlib.util.module_from_spec(spec);spec.loader.exec_module(window)
    if action=='prepare':
        assert confirmed,'Explicit returned phone window required'
        result_raw=(PRIVATE/'r7-stage/result.json').read_bytes();result=json.loads(result_raw)
        assert result['staged'] and result['terminal'] and not result.get('receipt_error')
        stage=json.loads((PRIVATE/'r7-stage/launch-request-private.json').read_text())
        expected=json.loads((CANDIDATE/'generation-result.json').read_text())['files']
        tested=json.loads((CANDIDATE/'test-result.json').read_text());assert tested['passed']
        workers={}
        for name in ['r7-quiesce-review.py','r7-restart-review.py']:
            raw=(CANDIDATE/name).read_bytes();assert sha(raw)==expected[name]['candidate_sha256']
            workers[name]={'base64':base64.b64encode(raw).decode(),'sha256':sha(raw)}
        data={'transaction_id':'charging-r7-'+secrets.token_hex(12),'stage_transaction':stage['transaction'],
              'stage_receipt_sha256':sha(result_raw),'expected_boot':stage['expected_boot'],'workers':workers}
        marker('prepare-request-private.json',{k:v for k,v in data.items() if k!='workers'})
        code=PREPARE
    elif action=='finish-bootloader':
        assert (OUT/'restart-request-private.json').exists()
        fb='/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
        q=subprocess.run([fb,'devices'],capture_output=True,timeout=15,check=True)
        found=re.findall(r'(?m)^(\S+)\s+fastboot\s*$',q.stdout.decode())
        expected=json.loads((PRIVATE.parent/'kernel109/fastboot-identity.json').read_text())['serial']
        assert found==[expected], 'Fresh exact single fastboot identity required'
        q=subprocess.run([fb,'-s',expected,'getvar','product'],capture_output=True,timeout=15,check=True)
        assert re.search(r'product:\s*msmnile\b',(q.stdout+q.stderr).decode())
        marker('fastboot-reboot-request-private.json',{'request_count':1,'partitions_written':[]})
        q=subprocess.run([fb,'-s',expected,'reboot'],capture_output=True,timeout=20,check=True)
        (OUT/'fastboot-reboot-private.txt').write_bytes(q.stdout+q.stderr)
        print(json.dumps({'reboot_requested_once':True,'partitions_written':[]}));return 0
    else:
        prepared=json.loads((OUT/'prepare-stdout-private.json').read_text())
        guard=prepared['guard'];base=prepared['base']
        data={'base':base,'transaction_id':guard['transaction_id']}
        if action=='quiesce':
            assert confirmed
            data['guard_sha256']=sha((OUT/'guard-private.json').read_bytes())
            data['worker_sha256']=sha((CANDIDATE/'r7-quiesce-review.py').read_bytes())
            marker('quiesce-request-private.json',data);code=QUIESCE
        elif action=='fetch-quiesce':code=FETCH
        elif action in ['inspect-restart','restart']:
            done=json.loads((OUT/'quiesce-summary-private.json').read_text())
            assert done['taint']==0 and done['transaction_id']==guard['transaction_id']
            assert json.loads((OUT/'quiesce-state-private.json').read_text())['exit_code']==0
            fetch=json.loads((OUT/'fetch-quiesce-stdout-private.json').read_text())
            assert fetch['process_state'] in ['absent','pid_reused']
            if action=='restart':
                assert confirmed
                inspected=json.loads((OUT/'inspect-restart-stdout-private.json').read_text())
                assert inspected['current_boot_guard_pass'] and inspected['quiesce_pass'] and inspected['inspect_only']
                marker('restart-request-private.json',{'request_count':1,'partitions_written':[],**data})
            worker=base+'/r7-restart-review.py';guard_path=base+'/guard-private.json'
            option='--inspect' if action=='inspect-restart' else '--commit-restart2-bootloader'
            digest=sha((CANDIDATE/'r7-restart-review.py').read_bytes())
            code=('from pathlib import Path\nimport hashlib,runpy,sys\n'
                  f'assert hashlib.sha256(Path({worker!r}).read_bytes()).hexdigest()=={digest!r}\n'
                  f'sys.argv=[{worker!r},"--guard",{guard_path!r},{option!r}]\n'
                  f'runpy.run_path({worker!r},run_name="__main__")\n')
        else:raise ValueError(action)
    q=window.host.ssh('python3 -c '+shlex.quote(code),input=json.dumps(data).encode(),timeout=35,check=False)
    (OUT/(action+'-stdout-private.json')).write_bytes(q.stdout)
    (OUT/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if action=='restart':
        print(json.dumps({'phase':action,'ssh_return':q.returncode,'output':q.stdout.decode(errors='replace')[-1800:]}));return 0
    if q.returncode:
        print(q.stderr.decode(errors='replace')[-2400:]);return q.returncode
    value=json.loads(q.stdout)
    if action=='prepare':
        # Keep exact remote guard bytes, including its serialization, for launch.
        guard_raw=json.dumps(value['guard'],indent=2).encode();(OUT/'guard-private.json').write_bytes(guard_raw)
        print(json.dumps({'prepared':True,'disk_r7_live_r6':True,'taint':0}))
    elif action=='fetch-quiesce':
        for name,entry in value['files'].items():
            assert '/' not in name and '\\' not in name
            raw=base64.b64decode(entry['base64'],validate=True);assert sha(raw)==entry['sha256']
            (OUT/name).write_bytes(raw)
        if 'summary.json' in value['files']:
            (OUT/'quiesce-summary-private.json').write_bytes((OUT/'summary.json').read_bytes())
        if 'state-private.json' in value['files']:
            (OUT/'quiesce-state-private.json').write_bytes((OUT/'state-private.json').read_bytes())
        state=json.loads((OUT/'state-private.json').read_text()) if 'state-private.json' in value['files'] else None
        failure=(OUT/'failure-private.txt').read_text()[-2500:] if 'failure-private.txt' in value['files'] else None
        print(json.dumps({'process_state':value['process_state'],
                          'state':{k:v for k,v in (state or {}).items() if k not in ['boot_id','transaction_id']},
                          'failure':failure,'log':value['log']},indent=2))
    elif action=='quiesce':print(json.dumps({'launched':True,'pid':value['pid']}))
    else: print(json.dumps(value,indent=2))
    return 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','quiesce','fetch-quiesce','inspect-restart','restart','finish-bootloader'])
    p.add_argument('--window-confirmed',action='store_true');args=p.parse_args()
    raise SystemExit(main(args.action,args.window_confirmed))
