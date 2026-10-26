"""Only new capture/wire boundaries. Existing C decoder and saved C-output fixtures reused."""
from pathlib import Path
import ast, base64, contextlib, copy, hashlib, importlib.util, json, os, subprocess, sys, tempfile, unittest.mock as mock

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'protection-evidence-parser-candidate'
CACHE = Path('/home/cy122/charging-management-20261023/protection-evidence-parser-01')
PRIVATE = Path(os.environ.get('SAMURAI_CAPTURE_TEST_OUTPUT', '/mnt/e/edk2-samurai-out/charging-oem-audit-20261023/protection-capture-tests-private-01'))
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def load(path, name):
    spec = importlib.util.spec_from_file_location(name,path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

worker = load(HERE/'stage-worker.py','actual_capture_worker')
host = load(HERE/'host.py','actual_capture_host')
fixtures = {n: (CACHE/f'actual-{n:02d}.txt').read_bytes() for n in (0,3,7,11)}
parser_path = OLD/'parse-evidence.py'
assert sha((CACHE/'frame-decoder').read_bytes()) == host.DECODER_SHA

def request():
    boot = '12345678-1234-4321-8765-123456789abc'
    return {'schema':'samurai-protection-capture-request-v1','transaction_id':'protection-capture-test-00000001',
        'identity':{'boot_id':boot,'version':worker.VERSION,'serial_sha256':'1'*64,'compatible_sha256':'2'*64,'rootfs_sha256':'3'*64},
        'adoption':{'transaction_id':'usb-irq-protection-activate-test-00000001',
            'guard_path':'/var/lib/samurai/usb-irq-protection-activate-test-00000001-adopted/boot-id-private.txt',
            'guard_sha256':sha((boot+'\n').encode()),'postboot_raw_sha256':'4'*64,'fresh_validation_sha256':'5'*64},
        'worker_sha256':sha((HERE/'stage-worker.py').read_bytes()),'lease_token':'6'*48}

class FakeDevice:
    """Only OS/sysfs/flock/time boundary fake; capture() itself is production code."""
    def __init__(self, req, after=0):
        self.request_sha256 = sha(worker.encode(req)); self.req=req; self.after=after
        h=worker.cached_header(fixtures[after]); self.batch_start=int(h['started_ns']); self.batch_end=int(h['ended_ns'])
        self.attempted=False; self.claimed=False; self.stores=0; self.raws={}; self.result=None
        self.old=False; self.failwrite=False; self.already=False; self.changed=False; self.identity_calls=0; self.locked_now=False
        self.clock=iter([max(0,self.batch_start-10),max(0,self.batch_start-2),self.batch_end+2,self.batch_end+3,self.batch_end+5])
    def now(self): return next(self.clock)
    def begin(self, req):
        if self.claimed: raise FileExistsError('once claim')
        self.claimed=True
    @contextlib.contextmanager
    def locked(self):
        self.locked_now=True
        try: yield
        finally: self.locked_now=False
    def open_instance(self): assert self.locked_now
    def check_window(self, req): assert self.locked_now
    def identity(self, req):
        assert self.locked_now; self.identity_calls+=1
        if self.old: raise ValueError('old resident protection note')
        result={**req['identity'],'guard_sha256':req['adoption']['guard_sha256'],'manifest_sha256':worker.MANIFEST,
                'protection_ko_sha256':worker.KO,'loaded_note_sha256':worker.NOTE,'instance_inode':99,
                'attributes':{'mac_evidence':[1,100],'mac_evidence_capture':[1,101]}}
        if self.changed and self.identity_calls>=3: result['instance_inode']=100
        return result
    def cache(self): return fixtures[self.after if self.attempted else 0 if self.already else 11]
    def raw(self,name,raw):
        assert name not in self.raws; self.raws[name]=raw
    def store_capture(self):
        assert self.locked_now; self.stores+=1; self.attempted=True
        if self.failwrite: raise OSError(5,'known failed batch store')
        code = int(worker.cached_header(fixtures[self.after])['error'])
        if code: raise OSError(-code,'saved kernel batch error')
        return 8
    def close(self): assert not self.locked_now
    def publish(self,result): self.result=copy.deepcopy(result)

cases=[]
def passed(label): cases.append({'case':label,'passed':True})

def run_worker_cases():
    req=request()
    dev=FakeDevice(req); result=worker.capture(req,dev)
    assert result['worker_complete'] and result['identity_match'] and dev.stores==1
    assert dev.raws['cache-after-private.txt']==fixtures[0]
    passed('actual capture uses one store under flock and retains exact cached output')
    dev=FakeDevice(req); dev.old=True; result=worker.capture(req,dev)
    assert dev.stores==0 and not result['worker_complete'] and dev.raws['cache-after-private.txt']==fixtures[11]
    passed('old protection identity rejects before capture store and retains rejection cache')
    dev=FakeDevice(req); dev.already=True; result=worker.capture(req,dev)
    assert dev.stores==0 and not result['worker_complete'] and 'already attempted' in result['errors'][0]['message']
    passed('already-attempted instance is not rearmed')
    dev=FakeDevice(req,3); dev.failwrite=True; result=worker.capture(req,dev)
    assert dev.stores==1 and result['write_error']['errno']==5 and result['observation_retained'] and dev.raws['cache-after-private.txt']==fixtures[3]
    passed('failed store consumes only one attempt and retains actual failed-report bytes/errno')
    dev=FakeDevice(req); dev.claimed=True; result=worker.capture(req,dev)
    assert dev.stores==0 and not result['worker_complete']
    passed('exclusive worker claim refuses a second execution')
    dev=FakeDevice(req); dev.changed=True; result=worker.capture(req,dev)
    assert dev.stores==1 and not result['identity_match'] and not result['worker_complete']
    passed('same-instance identity change remains unaccepted after raw retention')

def saved_case(directory, mode=0):
    req=request(); reqraw=worker.encode(req); dev=FakeDevice(req,mode)
    if mode==3: dev.failwrite=True
    result=worker.capture(req,dev); tx=req['transaction_id']; root='/root/charging-management-20261023/'+tx
    argv=['python3','-B',root+'/stage-worker.py','--execute-stage']; sup_argv=['python3','-B',root+'/stage-supervisor.py','--execute-supervisor']
    shared={'transaction_id':tx,'boot_id':req['identity']['boot_id'],'request_sha256':sha(reqraw)}
    sup={**shared,'pid':600,'start_ticks':60,'argv':sup_argv}
    launch={**shared,'supervisor_pid':600,'pid':700,'start_ticks':70,'argv':argv}
    term={k:v for k,v in launch.items() if k != 'start_ticks'}; term.update(terminal=True,returncode=0)
    supterm={**sup,'terminal':True,'returncode':0,'worker_pid':700,'worker_returncode':0}
    proc={k:v for k,v in launch.items() if k not in ('supervisor_pid','request_sha256')}; proc['worker_sha256']=req['worker_sha256']
    raw={**dev.raws,'request-private.json':reqraw,'result.json':worker.encode(result),'process-private.json':worker.encode(proc),
        'worker-launch-receipt-private.json':worker.encode(launch),'worker-terminal-private.json':worker.encode(term),
        'supervisor-process-private.json':worker.encode(sup),'supervisor-terminal-private.json':worker.encode(supterm),
        'launch-receipt-private.json':worker.encode(sup)}
    response={'transaction_id':tx,'request_sha256':sha(reqraw),'worker_result':result,'worker_terminal':term,
              'supervisor_receipt':sup,'worker_terminal_verified':True,'process':{'state':'absent'},'supervisor_process':{'state':'absent'}}
    def write():
        directory.mkdir(); (directory/'raw').mkdir()
        response['files']={}
        for name,value in raw.items():
            (directory/'raw'/name).write_bytes(value)
            response['files'][name]={'base64':base64.b64encode(value).decode(),'sha256':sha(value),'bytes':len(value)}
        (directory/'received-result-private.json').write_bytes(worker.encode(response))
    return req,reqraw,raw,response,write

def run_fetch_cases():
    pins={'parser':{'path':str(parser_path)},'worker':{'sha256':request()['worker_sha256']}}
    with mock.patch.object(host,'source_check',return_value=(pins,{})):
        for mode in (0,3,7):
            directory=PRIVATE/f'fetch-{mode}'
            req,reqraw,raw,response,write=saved_case(directory,mode); write()
            result=host.review_fetch(directory,req,reqraw,decoder=CACHE/'frame-decoder')
            assert result['source_authenticated'] and result['batch_time_bound'],result
            assert result['sequence_complete']==(mode==0)
            assert result['parsed']['decoder_sha256']==host.DECODER_SHA
            assert not result['parsed']['compatibility_verified'] and not result['parsed']['freshness_verified']
            assert result['TCA_classification']=='UNVERIFIED'
            passed('actual parse_saved + existing 58aa C decoder wired to saved provider mode '+str(mode))
        for n,change in enumerate(('worker_nonzero','supervisor_unknown','source_mismatch','raw_mismatch','terminal_input_mismatch',
                                   'EALREADY','unattempted_cache','store_not_attempted')):
            directory=PRIVATE/('reject-'+str(n)); req,reqraw,raw,response,write=saved_case(directory)
            if change=='worker_nonzero':
                term=json.loads(raw['worker-terminal-private.json']); term['returncode']=1
                raw['worker-terminal-private.json']=worker.encode(term); response['worker_terminal']=term
            elif change=='supervisor_unknown': response['supervisor_process']={'state':'unknown'}
            elif change=='source_mismatch':
                result=json.loads(raw['result.json']); result['identity_after']['boot_id']='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
                raw['result.json']=worker.encode(result); response['worker_result']=result
            elif change=='raw_mismatch':
                result=json.loads(raw['result.json']); result['raw_after_sha256']='0'*64
                raw['result.json']=worker.encode(result); response['worker_result']=result
            elif change=='terminal_input_mismatch':
                term=json.loads(raw['worker-terminal-private.json']); term['request_sha256']='0'*64
                raw['worker-terminal-private.json']=worker.encode(term); response['worker_terminal']=term
            else:
                result=json.loads(raw['result.json'])
                if change=='EALREADY': result.update(write_return=None,write_error={'type':'OSError','errno':114,'message':'already'})
                elif change=='unattempted_cache':
                    raw['cache-after-private.txt']=fixtures[11]; result['raw_after_sha256']=sha(fixtures[11])
                    result.update(write_return=None,write_error={'type':'OSError','errno':5,'message':'before kernel store'})
                else: result['capture_write_attempted']=False
                raw['result.json']=worker.encode(result); response['worker_result']=result
            write(); result=host.review_fetch(directory,req,reqraw,decoder=CACHE/'frame-decoder')
            assert not result['source_authenticated'] and result['errors'] and not result['runtime_retry_permitted']
            assert (directory/'raw/cache-after-private.txt').read_bytes()==(fixtures[11] if change=='unattempted_cache' else fixtures[0])
            passed('fetch retains raw but refuses promotion: '+change)

def run_actual_supervisor_case():
    """Original supervise runs unchanged, spawning/waiting a harmless local fixture child."""
    rootbase=PRIVATE/'actual-supervisor'; rootbase.mkdir()
    req=request(); root=rootbase/req['transaction_id']; root.mkdir()
    fixture_worker=b'''from pathlib import Path
import hashlib,json,os,sys,time
r=json.loads(sys.stdin.buffer.read()); root=Path(__file__).resolve().parent
out=root/'device-stage'; out.mkdir()
for name in ('cache-before-private.txt','cache-after-private.txt','result.json'):
 out.joinpath(name).write_bytes(root.joinpath('fixture-'+name).read_bytes())
fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
p={'transaction_id':r['transaction_id'],'boot_id':r['identity']['boot_id'],'pid':os.getpid(),
 'start_ticks':int(fields[19]),'argv':[x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(b'\\0') if x],
 'worker_sha256':r['worker_sha256']}
out.joinpath('process-private.json').write_text(json.dumps(p)+'\\n')
out.joinpath('request-private.json').write_bytes(root.joinpath('request-private.json').read_bytes())
time.sleep(0.05)
'''
    req['worker_sha256']=sha(fixture_worker); reqraw=worker.encode(req)
    dev=FakeDevice(req); result=worker.capture(req,dev)
    for name,data in dev.raws.items(): root.joinpath('fixture-'+name).write_bytes(data)
    root.joinpath('fixture-result.json').write_bytes(worker.encode(result))
    root.joinpath('stage-worker.py').write_bytes(fixture_worker)
    supervisor=(HERE/'supervisor.py').read_bytes(); root.joinpath('stage-supervisor.py').write_bytes(supervisor)
    root.joinpath('request-private.json').write_bytes(reqraw)
    root.joinpath('launch-claim-private.json').write_bytes(worker.encode({'transaction_id':req['transaction_id'],
        'request_sha256':sha(reqraw),'supervisor_sha256':sha(supervisor)}))
    argv=['python3','-B',str(root/'stage-supervisor.py'),'--execute-supervisor']
    with root.joinpath('owner-stdout-private.log').open('xb') as stdout,root.joinpath('owner-stderr-private.log').open('xb') as stderr:
        child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
        try:
            fields=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
            launched={'transaction_id':req['transaction_id'],'boot_id':req['identity']['boot_id'],
                'request_sha256':sha(reqraw),'pid':child.pid,'start_ticks':int(fields[19]),'argv':argv}
        finally: rc=child.wait()
    assert rc==0 and not root.joinpath('owner-stderr-private.log').read_bytes()
    raw={p.name:p.read_bytes() for p in (root/'device-stage').iterdir()}
    for name in ('supervisor-process-private.json','supervisor-terminal-private.json','worker-launch-receipt-private.json','worker-terminal-private.json'):
        raw[name]=root.joinpath(name).read_bytes()
    raw['launch-receipt-private.json']=worker.encode(launched)
    term=json.loads(raw['worker-terminal-private.json'])
    assert set(term)=={'transaction_id','boot_id','request_sha256','supervisor_pid','pid','argv','terminal','returncode'} and 'start_ticks' not in term
    assert not Path('/proc',str(child.pid)).exists() and not Path('/proc',str(term['pid'])).exists()
    call=PRIVATE/'actual-supervisor-fetch'; call.mkdir(); (call/'raw').mkdir()
    response={'transaction_id':req['transaction_id'],'request_sha256':sha(reqraw),'files':{},'worker_terminal_verified':True,
       'worker_terminal':term,'worker_result':result,'supervisor_receipt':launched,'process':{'state':'absent'},'supervisor_process':{'state':'absent'}}
    for name,value in raw.items():
        call.joinpath('raw',name).write_bytes(value)
        response['files'][name]={'bytes':len(value),'sha256':sha(value),'base64':base64.b64encode(value).decode()}
    call.joinpath('received-result-private.json').write_bytes(worker.encode(response))
    with mock.patch.object(host,'REMOTE_ROOT',str(rootbase)),mock.patch.object(host,'source_check',return_value=(
        {'parser':{'path':str(parser_path)},'worker':{'sha256':sha(fixture_worker)}},{})):
        reviewed=host.review_fetch(call,req,reqraw,decoder=CACHE/'frame-decoder')
    assert reviewed['source_authenticated'] and reviewed['batch_time_bound'] and reviewed['sequence_complete'],reviewed
    passed('actual original supervisor.supervise creates no-ticks terminal; real harmless child wait0 receipts pass actual review_fetch')

def run_owner_and_bind_cases():
    old=HERE.parent/'usb-irq-protection-stage-host-candidate-r2'
    assert (HERE/'supervisor.py').read_bytes()==(old/'supervisor.py').read_bytes()
    source=load(HERE/'prepare-sources.py','capture_derivation')
    assert (HERE/'remote.py').read_bytes()==source.derived_remote((old/'remote.py').read_bytes())
    original=load(old/'host.py','capture_original_owner')
    adapter=host.transport_module()
    assert ast.dump(ast.parse(__import__('inspect').getsource(original.transfer)))==ast.dump(ast.parse(__import__('inspect').getsource(adapter.transfer)))
    assert 'finally:' in (HERE/'supervisor.py').read_text() and 'rc = child.wait()' in (HERE/'supervisor.py').read_text()
    passed('original supervisor and actual R2 transfer/EOF/finally-wait are unchanged; only four remote strings differ')
    out=PRIVATE/'missing-adoption-runtime'
    class Missing:
        def review_adoption(self,*args): raise ValueError('no actual IRQ adoption')
    with mock.patch.object(host,'source_check',return_value=({'adoption_review':{'path':'fake'},'worker':{'sha256':'0'*64}},{})),\
         mock.patch.object(host,'load',return_value=Missing()),mock.patch.object(host,'PRIVATE',out):
        try: host.bind('protection-capture-test-00000001','missing','missing','missing','missing')
        except ValueError: pass
        else: raise AssertionError('missing actual adoption accepted')
    assert not out.exists()
    passed('actual bind refuses missing adoption before runtime mkdir/request/lease')
    # Execute actual old transfer's once gate. No key import/Popen is reachable.
    tx=request()['transaction_id']; once=PRIVATE/'once'; once.mkdir(); (once/'launch-intent-private.json').write_text('{}')
    with mock.patch.object(adapter,'bound',return_value=(once,{},request(),b'{}',{})),\
         mock.patch.object(adapter.subprocess,'Popen',side_effect=AssertionError('must not reconnect')):
        try: adapter.transfer('launch',tx,True)
        except ValueError as error: assert 'claimed' in str(error)
        else: raise AssertionError('unknown launch replay accepted')
    passed('original launch intent blocks replay even with unknown earlier child')

def main():
    PRIVATE.mkdir(mode=0o700,exist_ok=False)
    before={str(p):sha(p.read_bytes()) for p in [parser_path,CACHE/'frame-decoder',*(CACHE/f'actual-{n:02d}.txt' for n in fixtures)]}
    run_worker_cases(); run_fetch_cases(); run_actual_supervisor_case(); run_owner_and_bind_cases()
    assert before=={p:sha(Path(p).read_bytes()) for p in before}
    result={'passed':True,'new_case_count':len(cases),'cases':cases,'tested_files':{p.name:sha(p.read_bytes()) for p in
       [HERE/'stage-worker.py',HERE/'host.py',HERE/'remote.py',HERE/'supervisor.py',HERE/'prepare-sources.py',HERE/'test-delta.py']},
       'existing_saved_fixture_inputs':before,'original_inputs_unchanged':True,'private_output':str(PRIVATE),
       'actual_parser_function_and_existing_decoder_executed':True,'new_capture_runtime_identity_and_hardware_IO':'fake boundaries only',
       'device_or_transport_accessed':False,'old21_26_owner_matrices_rerun':False}
    (HERE/'test-result.json').write_bytes(worker.encode(result)); print(json.dumps({'passed':True,'new_case_count':len(cases)}))

if __name__=='__main__': main()
