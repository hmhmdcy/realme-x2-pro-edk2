"""Default source-only. Adopt a real passed IRQ/cohort new boot exactly once."""
from pathlib import Path
import argparse,ast,base64,hashlib,importlib.util,json,os,re,subprocess,sys
if sys.flags.optimize:raise RuntimeError('optimized interpreter is unsupported')
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
HOST=REF/'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate'
DEVICE=REF/'charging-oem-audit-20261023/irq-cohort-postboot-readonly'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def need(value,message):
    if not value:raise ValueError(message)

def create(path,raw):
    path=Path(path)
    with path.open('xb') as file:file.write(raw);file.flush();os.fsync(file.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def save(path,value):create(path,(json.dumps(value,indent=2)+'\n').encode())

def sources():
    pins=json.loads((HERE/'source-pins.json').read_bytes())
    need(set(pins)=={'host_delivery','host','device_delivery','device','operator_delivery','old_adopt'},'source pin set')
    raw={}
    for name,entry in pins.items():
        value=(REF/entry['path']).read_bytes();need(sha(value)==entry['sha256'],'frozen source changed: '+name);raw[name]=value
    for name in ['host_delivery','device_delivery','operator_delivery']:
        delivery=json.loads(raw[name])
        if name!='device_delivery':need(delivery['passed'] is True,'unpassed source delivery')
        else:need(delivery['revision']==2 and delivery['archive_revision']==3,'device archive revision differs')
        folder=(REF/pins[name]['path']).parent
        for filename,row in delivery['files'].items():
            expected=row['sha256'] if isinstance(row,dict) else row
            need(sha((folder/filename).read_bytes())==expected,'frozen delivery member changed: '+filename)
    ast.parse(raw['host']);ast.parse(raw['device'])
    tail=(HERE/'adopt-device-tail.inc').read_bytes();ast.parse(tail)
    need(b'/dev/mem' not in raw['device'] and b'mmap' not in raw['device'],'unexpected MMIO collector')
    return pins,raw

def host_module():
    sources();spec=importlib.util.spec_from_file_location('irq_adoption_verified_host',HOST/'host.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def review(context_path,camera_path,probe_directory,capture_directory):
    host=host_module();context_path=Path(context_path).resolve();capture_directory=Path(capture_directory).resolve()
    evaluated=host.evaluate_response(context_path,camera_path,probe_directory,capture_directory)
    need(evaluated['passed'] is True and evaluated['transport_returncode']==0 and evaluated['hardware_writes']==0
         and not evaluated.get('errors') and len(evaluated['checks'])==10,'actual complete IRQ postboot required')
    request=host.make_request(context_path,camera_path,probe_directory)
    tx=request['activation_transaction_id']
    need(re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}',tx) and context_path.parent.name==tx,'actual activation namespace')
    need(capture_directory.is_relative_to(context_path.parent),'capture must belong to this activation')
    report_raw=(capture_directory/'stdout-private.json').read_bytes();report=json.loads(report_raw)
    raw=report['raw'];before=raw['identity_before']
    need(before==raw['identity_after'] and before['boot_id']==request['new_boot_id']
         and before['boot_id']!=request['activation_guard']['boot_id'],'actual new boot changed')
    need(before['uname']['version']=='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026','exact Image502 required')
    need(raw['boot_partition']['sha256']=='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
         and raw['logdump_partition']['sha256']=='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
         and raw['manifest']['sha256']=='5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417','exact new cohort carriers')
    descriptor={'schema':'samurai-usb-irq-protection-adoption-v1','transaction_id':tx,
        'stage_transaction_id':request['guard']['transaction_id'],'boot':before['boot_id'],
        'old_boot':request['activation_guard']['boot_id'],'release':before['uname']['release'],
        'version':before['uname']['version'],'rootfs':before['rootfs']['sha256'],
        'serial_sha256':before['serial_sha256'],'compatible_sha256':sha(base64.b64decode(before['compatible_b64'],validate=True)),
        'guard':'/var/lib/samurai/'+tx+'-adopted/boot-id-private.txt',
        'manifest':raw['manifest']['sha256'],'candidate_boot_sha256':raw['boot_partition']['sha256'],
        'candidate_logdump_sha256':raw['logdump_partition']['sha256'],
        'context_sha256':request['context_sha256'],'activation_guard_sha256':request['guard_sha256'],
        'postboot_raw_sha256':sha(report_raw),'postboot_request_sha256':sha((json.dumps(request,sort_keys=True)+'\n').encode()),
        'postboot_request':request,'previous_adoption':request['activation_guard']['adoption'],
        'endpoint':request['new_endpoint']}
    return descriptor,sources()[1]

def payload(adoption,raw):
    source=raw['device'].split(b"\nif __name__=='__main__':",1)
    need(len(source)==2,'frozen collector main delimiter')
    prefix=b'import sys\nif sys.flags.optimize:raise RuntimeError("optimized adoption is unsupported")\n'
    return prefix+('ADOPTION='+repr(adoption)+'\n').encode()+source[0]+b'\n'+(HERE/'adopt-device-tail.inc').read_bytes()

def check_previous(previous,adoption):
    source=adoption['previous_adoption']
    need(previous['guard_path']==source['guard_path'] and previous['original_key_verified'] is True
         and previous['baseline481_verified'] is True and previous['Image502_verified'] is True,'actual source502 pointer required')
    need(previous['candidate_boot_sha256']=='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
         and previous['candidate_logdump_sha256']==adoption['candidate_logdump_sha256']
         and previous['charging_manifest_sha256']=='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
         and previous['postboot_raw_sha256']==source['postboot_raw_sha256'],'previous source carrier/manifest/postboot differs')
    need(adoption['guard']!=previous['guard_path'],'source guard cannot be reused')

def process_identity(child,argv):
    directory=Path('/proc',str(child.pid));stat=directory.joinpath('stat').read_text();fields=stat[stat.rindex(')')+2:].split()
    actual=[part.decode() for part in directory.joinpath('cmdline').read_bytes().split(b'\0') if part]
    # WSL Windows interop can expose a cmdline different from Popen's argv.
    # This is still the one child we own and wait; retain both without treating
    # an unrelated later PID lookup as its original execution proof.
    need(child.pid>0 and int(fields[19])>0 and actual,'original strict-key process identity not captured')
    return {'pid':child.pid,'start_ticks':int(fields[19]),'argv':argv,'observed_argv':actual}

def transfer(out,code,host,endpoint):
    argv=host.transport_argv(endpoint);save(out/'dispatch-intent-private.json',
        {'request_count':1,'argv':argv,'stdin_sha256':sha(code),'no_replay':True})
    primary=None;errors=[];receipt=None;terminal=False
    with (out/'adopt-stdout-private.json').open('xb') as stdout,(out/'adopt-stderr-private.txt').open('xb') as stderr:
        child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,close_fds=True)
        try:
            receipt={**process_identity(child,argv),'stdin_sha256':sha(code)}
            save(out/'adopt-child-private.json',receipt)
            child.communicate(input=code)
        except BaseException as error:primary=error
        finally:
            try:
                if child.stdin is not None and not child.stdin.closed:child.stdin.close()
            except BaseException as error:errors.append({'phase':'stdin_close','error':repr(error)})
            try:child.wait();terminal=True
            except BaseException as error:errors.append({'phase':'same_child_wait','error':repr(error)})
            try:stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
            except BaseException as error:errors.append({'phase':'log_fsync','error':repr(error)})
            try:
                save(out/'adopt-terminal-private.json',{'pid':child.pid,'start_ticks':receipt['start_ticks'] if receipt else None,
                    'argv':argv,'observed_argv':receipt['observed_argv'] if receipt else None,
                    'stdin_sha256':sha(code),'terminal':terminal,'returncode':child.returncode,
                    'stdout_sha256':sha((out/'adopt-stdout-private.json').read_bytes()),
                    'stderr_sha256':sha((out/'adopt-stderr-private.txt').read_bytes()),
                    'primary_error':repr(primary) if primary is not None else None,'cleanup_errors':errors})
            except BaseException as error:errors.append({'phase':'terminal_receipt','error':repr(error)})
    if primary is not None:raise primary
    need(terminal and not errors and child.returncode==0,'adoption outcome unknown or failed; inspect original only')
    return json.loads((out/'adopt-stdout-private.json').read_bytes())

def publish(out,adoption,reply):
    fixed={'guard_created':True,'old_guards_preserved':True,'transaction_id':adoption['transaction_id'],
           'boot_id':adoption['boot'],'guard':adoption['guard'],'postboot_raw_sha256':adoption['postboot_raw_sha256'],
           'fresh_validation_passed':True,'cohort_verified':True,'charging_controls_written':False,'hardware_writes':0}
    need(all(reply.get(k)==v for k,v in fixed.items()),'actual fresh adoption reply differs')
    need(reply['guard_sha256']==sha((adoption['boot']+'\n').encode())
         and re.fullmatch('[0-9a-f]{64}',reply['fresh_validation_sha256']),'actual guard/proof readback required')
    pointer=BASE/'boot-adoption-private.json';before=(out/'boot-adoption-before-irq-private.json').read_bytes()
    need(pointer.read_bytes()==before,'global pointer changed; preserve original adoption evidence')
    current={'guard_path':adoption['guard'],'original_key_verified':True,'baseline481_verified':True,
        'Image502_verified':True,'USB_IRQ_protection_verified':True,'charging_manifest_sha256':adoption['manifest'],
        'candidate_boot_sha256':adoption['candidate_boot_sha256'],'candidate_logdump_sha256':adoption['candidate_logdump_sha256'],
        'postboot_raw_sha256':adoption['postboot_raw_sha256'],'fresh_validation_sha256':reply['fresh_validation_sha256'],
        'stage_transaction_id':adoption['stage_transaction_id']}
    endpoint={'kind':'usb-ipv6','peer':adoption['endpoint'],'interface_index':29,'host_key_alias':'169.254.42.1',
        'original_key_verified':True,'observed_new_boot':adoption['boot'],'guard_path':adoption['guard'],
        'postboot_Image502_passed':True,'postboot_USB_IRQ_protection_passed':True}
    save(out/'new-endpoint-private.json',endpoint);save(out/'adoption-pointer-private.json',current)
    temp=BASE/(adoption['transaction_id']+'-adoption-next-private.json')
    create(temp,(json.dumps(current,indent=2)+'\n').encode())
    need(pointer.read_bytes()==before,'global pointer changed before publish; keep prepared original')
    temp.replace(pointer)
    fd=os.open(BASE,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return current

def adopt(context,camera,probe,capture,window_confirmed=False):
    need(window_confirmed is True,'current coordinated window required')
    descriptor,raw=review(context,camera,probe,capture);host=host_module()
    out=Path(context).resolve().parent/'irq-adoption-01-private'
    need(not out.exists(),'adoption once intent already exists; inspect only')
    previous_raw=(BASE/'boot-adoption-private.json').read_bytes();check_previous(json.loads(previous_raw),descriptor)
    os.umask(0o077);out.mkdir(mode=0o700)
    create(out/'boot-adoption-before-irq-private.json',previous_raw)
    save(out/'adopt-request-private.json',descriptor);code=payload(descriptor,raw)
    create(out/'executed-adoption-source.py',code)
    reply=transfer(out,code,host,descriptor['endpoint'])
    pointer=publish(out,descriptor,reply)
    save(out/'adoption-result-private.json',{'passed':True,'pointer':pointer,'old_pointer_and_guards_preserved':True,
         'no_charge_or_USB_or_carrier_control_write':True})
    return {'adopted':True,'private_directory':str(out),'physical_delivery_or_latency_accepted':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['context','camera','probe-directory','capture-directory']:parser.add_argument('--'+name)
    parser.add_argument('--execute-adopt',action='store_true');parser.add_argument('--window-confirmed',action='store_true')
    args=parser.parse_args()
    if not args.execute_adopt:
        sources();print(json.dumps({'source_checked':True,'device_accessed':False,'runtime_identity_or_request_created':False}));return
    print(json.dumps(adopt(args.context,args.camera,args.probe_directory,args.capture_directory,args.window_confirmed)))

if __name__=='__main__':main()
