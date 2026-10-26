"""Once rollback transport adapter. Default software checks never bind or connect."""
from pathlib import Path
import argparse,base64,hashlib,importlib.util,json,os,re,secrets,subprocess,sys,time
if sys.flags.optimize:raise RuntimeError('nonoptimized Python required')
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def local(path):
    value = str(path).replace('\\', '/')
    if os.name != 'nt' and value.startswith('E:/'):
        value = '/mnt/e/' + value[3:]
    return Path(value)

def need(value, message):
    if not value:
        raise ValueError(message)

def create(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if os.name != 'nt':
        fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

def save(path, value):
    create(path, (json.dumps(value, indent=2) + '\n').encode())

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, local(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def process_identity(pid):
 p=Path('/proc',str(pid));fields=(p/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'startticks':int(fields[19]),'argv':[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]}

def process_status(receipt):
 try:
  now=process_identity(receipt['pid'])
  if now['startticks']!=receipt['startticks']:return 'pid_reused'
  fields=Path('/proc',str(receipt['pid']),'stat').read_text().rsplit(')',1)[1].split()
  return 'zombie' if fields[0]=='Z' else 'alive' if now['argv']==receipt['argv'] else 'unknown'
 except FileNotFoundError:return 'absent'
 except (OSError,KeyError,ValueError):return 'unknown'

PEER='fe80::62:bcff:fe28:a101%29'
ALIAS='169.254.42.1'
PRIVATE=local('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-rollback')


def source_check():
    pins=json.loads((HERE/'source-pins.json').read_bytes());values={}
    need(set(pins)=={'binder','binder_delivery','worker','worker_delivery','stage_delivery','key_transport','host','remote','supervisor'},'source pin set')
    for name,item in pins.items():
        raw=local(item['path']).read_bytes();need(sha(raw)==item['sha256'],'source changed: '+name);values[name]=raw
    need(pins['binder_delivery']['sha256']=='c8f53b5704cd73e601c7653a2b56372566e2f186bc877f558e64e2b6b3653745'
         and pins['binder']['sha256']=='6537bd2c0c500239c0289fd5f1c5114c719366830bcb0d7f76124511bd709b50','actual frozen binder')
    need(pins['worker_delivery']['sha256']=='8ac464757630d72fc5ce3da377501651e84bf8c7f74fc5fbffd4156914eddfad'
         and pins['worker']['sha256']=='f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142','exact restore algorithm')
    need(pins['stage_delivery']['sha256']=='ee53341c31c75970df3fdbe3a417fe5042aabd3096ec8717547a87de9751c956'
         and pins['key_transport']['sha256']=='7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c','original owner/key source')
    binder=load_module(pins['binder']['path'],'rollback_connected_frozen_binder');binder.source_check()
    return pins,values


def bind(transaction,profile,stage_directory,stage_fetch_directory,probe_directory,context=None):
    pins,_=source_check();binder=load_module(pins['binder']['path'],'rollback_connected_actual_bind')
    out=PRIVATE/transaction
    # Actual binder proves every source/action/current-identity fact before its
    # mkdir; do not create PRIVATE or derive a current UUID from old adoption.
    need(re.fullmatch(r'usb-irq-protection-rollback-[a-z0-9-]{8,48}',transaction),'new rollback transaction')
    binder.review_current(profile,stage_directory,stage_fetch_directory,probe_directory,context)
    PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    result=binder.bind(out,transaction,profile,stage_directory,stage_fetch_directory,probe_directory,context)
    request_raw=(out/'request-private.json').read_bytes();request=json.loads(request_raw)
    binding_raw=(out/'current-binding-private.json').read_bytes();current=json.loads(binding_raw)
    inputs=dict(profile=profile,stage_directory=str(Path(stage_directory).resolve()),stage_fetch_directory=str(Path(stage_fetch_directory).resolve()),
        probe_directory=str(Path(probe_directory).resolve()),context=str(Path(context).resolve()) if context else None)
    save(out/'binding-private.json',dict(schema='samurai-rollback-connected-binding-v1',transaction_id=transaction,
        request_sha256=sha(request_raw),current_binding_sha256=sha(binding_raw),source_pins_sha256=sha((HERE/'source-pins.json').read_bytes()),
        inputs=inputs,endpoint=dict(peer=current['new_endpoint'],host_key_alias=ALIAS,observed_new_boot=request['identity']['boot_id'])))
    return result


def bound(transaction,launching=False):
    need(re.fullmatch(r'usb-irq-protection-rollback-[a-z0-9-]{8,48}',transaction),'rollback transaction name')
    pins,_=source_check();out=PRIVATE/transaction
    request_raw=(out/'request-private.json').read_bytes();request=json.loads(request_raw);binding=json.loads((out/'binding-private.json').read_bytes())
    need(binding['transaction_id']==request['transaction_id']==transaction and binding['request_sha256']==sha(request_raw)
         and binding['current_binding_sha256']==sha((out/'current-binding-private.json').read_bytes())
         and binding['source_pins_sha256']==sha((HERE/'source-pins.json').read_bytes()),'retained original binding changed')
    need(sha((out/'restore-worker.py').read_bytes())==request['worker_sha256']==pins['worker']['sha256'],'original worker changed')
    if launching:
        binder=load_module(pins['binder']['path'],'rollback_connected_launch_reaudit');i=binding['inputs']
        reviewed=binder.review_current(i['profile'],local(i['stage_directory']),local(i['stage_fetch_directory']),local(i['probe_directory']),local(i['context']) if i['context'] else None)
        need(reviewed==json.loads((out/'current-binding-private.json').read_bytes()),'actual source/profile/current evidence changed')
        worker=load_module(pins['worker']['path'],'rollback_launch_request');worker.unpack(request)
        need(request['identity']==reviewed['identity'] and request['source_identity']==reviewed['saved']['source_identity']
             and request['source_stage']==reviewed['saved']['source_stage'] and request['activation']==reviewed['saved']['activation'],'actual request differs from original reviewed facts')
    return out,binding,request,request_raw,pins


def ssh_owner(job_path):
    job_path=Path(job_path);job=json.loads(job_path.read_bytes());directory=job_path.parent
    need(directory.is_relative_to(PRIVATE) and job['host_sha256']==sha(Path(__file__).read_bytes()),'original SSH owner source/path')
    code=Path(job['program']).read_bytes();need(sha(code)==job['stdin_sha256'],'original exact remote input')
    save(directory/'owner-process-private.json',process_identity(os.getpid()))
    argv=job['argv'];primary=None;cleanup=[];terminal=False;identity=None;child=None;stdout=None;stderr=None
    try:
        stdout=(directory/'stdout-private.json').open('xb');stderr=(directory/'stderr-private.txt').open('xb')
        child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,close_fds=True)
        identity=process_identity(child.pid)
        save(directory/'transport-child-private.json',dict(identity,requested_argv=argv,stdin_sha256=sha(code)))
        child.communicate(input=code)
    except BaseException as error:primary=error
    finally:
        if child is not None:
            try:
                if child.stdin is not None and not child.stdin.closed:child.stdin.close()
            except BaseException as error:cleanup.append(dict(phase='owned_stdin_close',error=repr(error)))
            try:child.wait();terminal=True
            except BaseException as error:cleanup.append(dict(phase='same_child_wait',error=repr(error)))
        for name,stream in (('stdout',stdout),('stderr',stderr)):
            if stream is None:continue
            try:stream.flush();os.fsync(stream.fileno())
            except BaseException as error:cleanup.append(dict(phase=name+'_fsync',error=repr(error)))
            try:stream.close()
            except BaseException as error:cleanup.append(dict(phase=name+'_close',error=repr(error)))
        # A clean terminal is published only after every owned log close.
        if child is not None:
            try:save(directory/'transport-terminal-private.json',dict(identity or {'pid':child.pid},requested_argv=argv,stdin_sha256=sha(code),
                terminal=terminal,returncode=child.returncode,stdout_sha256=sha((directory/'stdout-private.json').read_bytes()),stderr_sha256=sha((directory/'stderr-private.txt').read_bytes()),
                primary_error=repr(primary) if primary else None,cleanup_errors=cleanup))
            except BaseException as error:cleanup.append(dict(phase='terminal_receipt',error=repr(error)))
    if primary is not None:raise primary
    need(terminal and not cleanup,'original transport outcome uncertain; fetch same worker only')
    return child.returncode


def start_job(directory,action,code,argv,wait_seconds=35):
    call=directory/('launch-job-private' if action=='launch' else action+'-'+secrets.token_hex(8)+'-private');call.mkdir(mode=0o700)
    create(call/'executed-remote.py',code)
    owner_argv=[sys.executable,'-B',str(Path(__file__).resolve()),'--transport-job',str(call/'job-private.json')]
    save(call/'job-private.json',dict(action=action,program=str(call/'executed-remote.py'),stdin_sha256=sha(code),argv=argv,owner_argv=owner_argv,host_sha256=sha(Path(__file__).read_bytes())))
    with (call/'owner-private.log').open('xb') as log:
        child=subprocess.Popen(owner_argv,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    try:save(call/'owner-launch-private.json',process_identity(child.pid))
    except BaseException as error:
        try:save(call/'owner-receipt-error-private.json',dict(pid=child.pid,error=repr(error),unknown_means_fetch_only=True))
        except BaseException:pass
    try:rc=child.wait(timeout=wait_seconds)
    except subprocess.TimeoutExpired:return dict(pending=True,job=str(call),unknown_means_fetch_only=action=='launch')
    save(call/'owner-parent-terminal-private.json',dict(pid=child.pid,argv=owner_argv,terminal=True,returncode=rc))
    return dict(pending=False,job=str(call),owner_returncode=rc)


def terminal_job(call):
    call=Path(call);job=json.loads((call/'job-private.json').read_bytes());original=json.loads((call/'transport-child-private.json').read_bytes());term=json.loads((call/'transport-terminal-private.json').read_bytes())
    parent=json.loads((call/'owner-launch-private.json').read_bytes());owner=json.loads((call/'owner-process-private.json').read_bytes())
    need(job['host_sha256']==sha(Path(__file__).read_bytes()) and all(parent[k]==owner[k] for k in ('pid','startticks','argv'))
         and type(owner['pid']) is int and owner['pid']>0 and type(owner['startticks']) is int and owner['startticks']>0
         and owner['argv']==job['owner_argv'],'same original detached local owner')
    need(sha((call/'executed-remote.py').read_bytes())==job['stdin_sha256']==original['stdin_sha256']==term['stdin_sha256'],'same exact original input')
    need(type(original.get('pid')) is int and original['pid']>0 and type(original.get('startticks')) is int and original['startticks']>0
         and all(original[k]==term[k] for k in ('pid','startticks','argv','requested_argv')) and original['requested_argv']==job['argv'], 'same original SSH child')
    need(term['terminal'] is True and type(term['returncode']) is int and term['primary_error'] is None and not term['cleanup_errors'],'actual clean transport terminal required')
    need(term['stdout_sha256']==sha((call/'stdout-private.json').read_bytes()) and term['stderr_sha256']==sha((call/'stderr-private.txt').read_bytes()),'original output hashes')
    return term,json.loads((call/'stdout-private.json').read_bytes())


def accept_fetch(out,request,request_raw,response):
    need(response['transaction_id']==request['transaction_id'] and response['request_sha256']==sha(request_raw),'original remote response binding')
    result=dict(worker_result_retained=response.get('worker_result') is not None,rollback_staged_original=False,runtime_validation_accepted=False)
    files=response.get('files',{});raws={}
    for name,item in files.items():
        need(re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}',name),'fetched name')
        raw=base64.b64decode(item['base64'],validate=True);need(sha(raw)==item['sha256'] and len(raw)==item['bytes'],'raw fetched bytes');raws[name]=raw
    rawout=out/'raw';rawout.mkdir(mode=0o700)
    for name,raw in raws.items():create(rawout/name,raw)
    if response.get('worker_terminal_verified') is not True:return result
    if not all(name in raws for name in ('result.json','process-private.json','launch-receipt-private.json','worker-launch-receipt-private.json','worker-terminal-private.json','supervisor-process-private.json','supervisor-terminal-private.json')):return result
    worker=json.loads(raws['process-private.json']);launch=json.loads(raws['worker-launch-receipt-private.json']);end=json.loads(raws['worker-terminal-private.json']);sup=json.loads(raws['supervisor-process-private.json']);supend=json.loads(raws['supervisor-terminal-private.json'])
    parent=json.loads(raws['launch-receipt-private.json'])
    root='/root/charging-management-20261023/'+request['transaction_id'];argv=['python3','-B',root+'/restore-worker.py','--execute-rollback'];sup_argv=['python3','-B',root+'/rollback-supervisor.py','--execute-supervisor']
    for row in (worker,launch,end,sup,supend):need(row['transaction_id']==request['transaction_id'] and row['boot_id']==request['identity']['boot_id'],'same original device child transaction/boot')
    need(type(worker['pid']) is int and worker['pid']>0 and type(sup['pid']) is int and sup['pid']>0
         and worker['pid']==launch['pid']==end['pid']==supend['worker_pid'] and worker['argv']==launch['argv']==end['argv']==argv
         and type(worker['start_ticks']) is int and worker['start_ticks']>0 and launch['start_ticks'] in (None,worker['start_ticks']), 'original restore Popen instance')
    need(sup['pid']==launch['supervisor_pid']==end['supervisor_pid']==supend['pid'] and sup['argv']==supend['argv']==sup_argv
         and sup['start_ticks']==supend['start_ticks'] and type(sup['start_ticks']) is int and sup['start_ticks']>0,'original detached supervisor instance')
    need(parent['pid']==sup['pid'] and parent['argv']==sup_argv and parent['start_ticks'] in (None,sup['start_ticks'])
         and parent['transaction_id']==request['transaction_id'] and parent['boot_id']==request['identity']['boot_id'], 'original remote supervisor Popen receipt')
    need(worker['worker_sha256']==request['worker_sha256'] and all(row['request_sha256']==sha(request_raw) for row in (parent,launch,end,sup,supend)), 'original request/source chain')
    need(end['terminal'] is supend['terminal'] is True and type(end['returncode']) is type(supend['returncode']) is type(supend['worker_returncode']) is int
         and end['returncode']==supend['worker_returncode'] and supend['returncode']==0,'same original worker real terminal')
    result.update(worker_terminal_verified=True,worker_returncode=end['returncode'])
    need(response['worker_terminal']==end,'fetched actual worker terminal differs')
    if end['returncode']!=0:return result
    value=json.loads(raws['result.json']);need(value==response['worker_result'],'actual fetched result differs')
    need(value['transaction_id']==request['transaction_id'] and value['profile']==request['profile'] and value['terminal'] is True
         and value['restored'] is True and value['status']=='staged_original/runtime_pending' and value['runtime_pending'] is True
         and value['disk_state']=='all_original_fsynced' and value['stop_verified'] is True and value['primary_error'] is None
         and not value.get('receipt_error') and not value.get('close_error') and value['unknown_write_state'] is False,'original restore not qualified successful terminal')
    module=load_module(HERE.parent/'usb-irq-protection-rollback-candidate/restore-worker.py','rollback_final_fixed_identities')
    need(value['actual_resident_notes']==module.expected_profile(request)[1] and set(value['final_files'])==set(module.ORDER),'profile actual notes and exact files')
    for name,digest in module.OLD_FILES.items():need(value['final_files'][name]==dict(sha256=digest,mode='0o600',classification='original') and value['temporary_files'][name]['state']=='absent','exact original final disk')
    need(all(response.get(name,{}).get('state') in ('absent','zombie','source_boot_ended') for name in ('process','supervisor_process')),'original mutators not known ended')
    result['rollback_staged_original']=True;return result


def review_launch_transport(out,request,request_raw,response):
    original,launched=terminal_job(out/'launch-job-private')
    intent=json.loads((out/'launch-intent-private.json').read_bytes());job=json.loads((out/'launch-job-private/job-private.json').read_bytes())
    need(original['returncode']==0 and job['action']=='launch' and job['stdin_sha256']==intent['stdin_sha256']
         and intent['request_sha256']==sha(request_raw) and job['argv']==intent['argv'],'original launch input/action/terminal0 required')
    need(launched['transaction_id']==request['transaction_id'] and launched['request_sha256']==sha(request_raw)
         and launched['launched'] is True,'original launch response binding')
    parent=json.loads(base64.b64decode(response['files']['launch-receipt-private.json']['base64'],validate=True))
    launch_sup=launched['supervisor_receipt']
    need(all(launch_sup[k]==parent[k] for k in ('transaction_id','boot_id','request_sha256','pid','start_ticks','argv')),
         'same original launch supervisor receipt')
    return dict(original_launch_transport_terminal=True,original_launch_transport_returncode=original['returncode'])


def transfer(action,transaction,window_confirmed=False):
    need(action in ('launch','status','fetch'),'explicit transport action')
    need(os.name!='nt','connected actions require the original WSL /proc owner environment')
    out,binding,request,request_raw,pins=bound(transaction,launching=action=='launch')
    if action=='launch':
        need(window_confirmed is True,'current coordinated window required')
        need(not (out/'launch-intent-private.json').exists(),'launch consumed/unknown; status/fetch only')
    key=load_module(pins['key_transport']['path'],'rollback_original_key')
    endpoint=binding['endpoint'];need(endpoint==dict(peer=PEER,host_key_alias=ALIAS,observed_new_boot=request['identity']['boot_id']),'actual retained current endpoint')
    argv=[key.SSH,'-6','-T',*key.OPTIONS,'-o','HostKeyAlias='+ALIAS,'root@'+PEER,'python3 -']
    envelope=dict(action=action,request=request,request_sha256=sha(request_raw),request_base64=base64.b64encode(request_raw).decode(),
        worker_base64=base64.b64encode((out/'restore-worker.py').read_bytes()).decode() if action=='launch' else None,
        supervisor_base64=base64.b64encode((HERE/'supervisor.py').read_bytes()).decode() if action=='launch' else None,
        supervisor_sha256=pins['supervisor']['sha256'],window_confirmed=window_confirmed is True)
    code=('ROLLBACK_TRANSPORT='+repr(envelope)+'\n').encode()+(HERE/'remote.py').read_bytes()
    if action=='launch':save(out/'launch-intent-private.json',dict(transaction_id=transaction,request_count=1,request_sha256=sha(request_raw),stdin_sha256=sha(code),argv=argv,unknown_means_fetch_only=True))
    started=start_job(out,action,code,argv)
    if started['pending']:return started
    term,response=terminal_job(started['job']);need(term['returncode']==0,'original transport nonzero/unknown; fetch only')
    need(response['transaction_id']==transaction and response['request_sha256']==sha(request_raw),'remote response bound to original request')
    save(Path(started['job'])/'received-result-private.json',response)
    if action=='fetch':
        qualification=accept_fetch(Path(started['job']),request,request_raw,response)
        # Even a device terminal cannot substitute for the exact original
        # launch-transport child wait. Preserve raw when its receipt is unknown.
        try:
            qualification.update(review_launch_transport(out,request,request_raw,response))
        except (OSError,ValueError,KeyError,TypeError) as error:
            qualification.update(original_launch_transport_terminal=False,rollback_staged_original=False,launch_transport_observation_error=type(error).__name__)
        started.update(qualification)
    return dict(started,response_process=response.get('process'),runtime_validation_accepted=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--action',choices=('check-local','bind','launch','status','fetch'),default='check-local')
    parser.add_argument('--transport-job');parser.add_argument('--transaction');parser.add_argument('--profile');parser.add_argument('--stage-directory');parser.add_argument('--stage-fetch-directory');parser.add_argument('--probe-directory');parser.add_argument('--context');parser.add_argument('--window-confirmed',action='store_true')
    args=parser.parse_args()
    if args.transport_job:raise SystemExit(ssh_owner(args.transport_job))
    if args.action=='check-local':source_check();value=dict(source_only=True,runtime_request_or_lease_generated=False,device_accessed=False)
    elif args.action=='bind':value=bind(args.transaction,args.profile,args.stage_directory,args.stage_fetch_directory,args.probe_directory,args.context)
    else:value=transfer(args.action,args.transaction,args.window_confirmed)
    print(json.dumps(value,indent=2))


if __name__=='__main__':main()
