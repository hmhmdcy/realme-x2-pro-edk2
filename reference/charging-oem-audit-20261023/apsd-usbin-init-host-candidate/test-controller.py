"""New controller boundaries only; real parser/gates/runner, fake OS/SSH boundary."""
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
from unittest.mock import patch
import ast
import json
import shutil
import subprocess
import tempfile
import common,protocol,gates,observer,controller,device

HERE=Path(__file__).resolve().parent
AUTHOR=HERE.parent/'apsd-usbin-init-candidate'
cases=[]
def check(name,condition):
    assert condition,name
    cases.append(name)
def rejects(fn):
    try:fn()
    except (ValueError,RuntimeError,FileExistsError,TimeoutError):return True
    return False

def actual_fixtures():
    out=HERE/'actual-fixtures';out.mkdir(exist_ok=True)
    for name in ['usbin-init-core.h','tested-functions.inc','tested-struct.inc']:
        shutil.copyfile(AUTHOR/name,out/name)
    prefix=(AUTHOR/'test-init.c').read_text().split('int main(void)')[0]
    tail=r'''
static void emit(const char *name){char buf[4096];state_show(&dev,NULL,buf);printf("%s\t%s",name,buf);}
int main(void){
 setup();assert(control("observe")==7);emit("observed");
 setup();assert(control("arm")==3);tick(1000);emit("waiting");
 setup();assert(control("arm")==3);stable();emit("verified");assert(control("commit")==6);emit("committed");
 setup();hw.cfg=0x40;assert(control("arm")==3);stable();emit("noop");
 setup();assert(control("arm")==3);tick(1000);tick(1250);delay_at=33;delay_ms=60000;tick(1500);
 assert(!writes&&d.state.old_valid&&!refs&&d.state.phase==UI_TIMEOUT);emit("blocked_timeout");return 0;
}
'''
    (out/'state-fixtures.c').write_text(prefix+tail)
    command=['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(out/'state-fixtures.c'),'-o',str(out/'state-fixtures')]
    built=subprocess.run(command,capture_output=True,text=True);assert built.returncode==0,built.stderr
    run=subprocess.run([str(out/'state-fixtures')],capture_output=True,text=True);assert run.returncode==0,run.stderr
    (out/'stdout.jsonl').write_text(run.stdout)
    return {name:protocol.parse(raw) for name,raw in (line.split('\t',1) for line in run.stdout.splitlines())}

def sample():
    telemetry={k:0 for k in ['error','stop_error','latched','fault','source_inhibit','cycle_timeout','thermal_inhibit','gauge_charge_stop','shadow','logical_full','hold_requested','full_holding','full_cause','session_seconds']}
    telemetry.update(valid=1,online=1,protection_ok=1,age_ms=500,flags=192,desired_enable=1,budget_ua=100000,temp_decic=258,thermal_band=4)
    source={'usb':{'online':1,'usb_type':'[SDP]','current_max':100000,'input_current_limit':100000},'charger':{'input_current_limit':100000,'constant_charge_current':250000,'constant_charge_voltage':8725000,'charge_behaviour':'[auto] inhibit-force-discharge','health':'Good','status':'Charging'}}
    return {'source_online':1,'acok_online':1,'source':source,'telemetry':telemetry,'raw_pmic':[17,1,16,8,35,43,6,192],'battery':{'status':'Discharging','current_now':-4000}}

def readiness(c,state,for_arm):
    receipt={'pid':123,'start_ticks':456,'argv':['python3','observer.py']};rows=[]
    for i,now in enumerate([2000,4200]):
        s=deepcopy(state);s['now_boottime_ms']=now;s['remaining_ms']=max(0,s['deadline_boottime_ms']-now)
        status={'pid':123,'start_ticks':456,'transaction':c['transaction'],'token':c['token'],'active':True,'terminal':False,'phase':'ready','realtime':10+i*2.2,'remaining_boottime_seconds':150-i*2.2,'ready_to_arm':for_arm,'latest_sample':sample(),'tick':4+i}
        rows.append({'status':status,'process':dict(receipt,state='alive'),'helper':{'fresh':True,'state':s},'remote_realtime':10.1+i*2.2,'remote_boottime_ms':now})
    return {'observations':rows,'observer_receipt':receipt,'identity_unchanged':True,'environment_unchanged':True,'uncertain':False}

def tests():
    f=actual_fixtures();c={'transaction':'usbin-init-test','token':'t','instance':f['observed']['instance']}
    check('actual observed and waiting schema',protocol.observed(f['observed']) and protocol.waiting(f['waiting'],1000,45000))
    check('actual changed clear and committed schema',protocol.verified(f['verified']) and protocol.committed(f['committed']))
    check('actual old-zero accepts no reference and no write',protocol.verified(f['noop']) and not f['noop']['held_ref'] and not f['noop']['write_attempted'])
    check('actual blocked-config expiry accepts saved old_valid and zero writes',f['blocked_timeout']['old_valid'] and protocol.expired_zero_write(f['blocked_timeout']))
    check('unarmed observed closes without configuration writes',protocol.close_zero_write(f['observed']) and not protocol.close_zero_write(f['waiting']) and not protocol.close_zero_write(f['verified']))
    bad=deepcopy(f['blocked_timeout']);bad['write_attempted']=True
    check('attempted-write timeout rejected',not protocol.expired_zero_write(bad))
    check('different instance rejected',rejects(lambda:protocol.parse(f['verified'],'000000000000ffff')))
    fieldset=set(json.loads((HERE/'helper-protocol.json').read_text())['fields'])
    check('all actual fields exactly match frozen protocol',all(set(s)==fieldset for s in f.values()))
    d=readiness(c,f['observed'],True);check('two fresh observer ticks permit arm only',gates.ready(d,c,True,.1)['ready_to_arm'])
    armed=readiness(c,f['waiting'],False);check('two fresh armed ticks permit physical prompt',gates.ready(armed,c,False,.1)['may_prompt_user'])
    for label,mutate in [
        ('helper bracket stale',lambda x:x['observations'][-1]['helper'].update(fresh=False)),
        ('PID reused',lambda x:x['observations'][-1]['process'].update(state='pid_reused')),
        ('tick not advancing',lambda x:x['observations'][-1]['status'].update(tick=4)),
        ('CV cap exceeded',lambda x:x['observations'][-1]['status']['latest_sample']['source']['charger'].update(constant_charge_voltage=8750000)),
        ('input already off',lambda x:x['observations'][-1]['status']['latest_sample'].update(raw_pmic=[0]*8)),
    ]:
        b=deepcopy(armed);mutate(b);check(label+' rejects prompt',not gates.ready(b,c,False,.1)['may_prompt_user'])
    b=deepcopy(armed);b['observations'][-1]['helper']['state']['deadline_boottime_ms']=4500
    check('insufficient arm time rejects prompt',not gates.ready(b,c,False,.1)['may_prompt_user'])

    # Unchanged icon parser is reused; only new aggregation/acceptance is tested.
    rows=[]
    for i in range(45):
        r=sample();r.update(t_start=i,t_end=i+.05,helper={'state':f['verified']})
        if 4<=i<14:r.update(source_online=0,acok_online=0)
        rows.append(r)
    raw={'samples':rows,'terminal_reason':'cycle_complete','identity_unchanged':True,'environment_unchanged':True,'monitor':{'started':True,'errors':[]},'capture_errors':[],'exception':None,'duration_seconds':45}
    result=observer.audit(raw)
    check('actual aggregation separates physical init and screen state',result['initialization_verified'] and result['physical_cycle_passed'] and result['cv_cap_preserved'] and not result['screen_latency_verified'] and result['ui_observation']['edges'][0]['battery_state_events']==[])
    for r in rows:r['source_online']=r['acok_online']=1
    check('bit clear and logical USB alone do not pass physical cycle',not observer.audit(raw)['physical_cycle_passed'])

    # Execute actual host run() against only a fake SSH return boundary.
    with tempfile.TemporaryDirectory() as tmp:
        private=Path(tmp);files={n:b'x' for n in controller.RUNTIME};inputs=(files,'boot','guard',{})
        calls=[];fail=[False]
        def ssh(command,**kwargs):
            program=kwargs['input'].decode();data=ast.literal_eval(program.split('io.BytesIO(',1)[1].split('))\n',1)[0]);incoming=json.loads(data)
            calls.append(incoming);a=incoming['action']
            if fail[0]:raise TimeoutError('normal disconnected transport')
            if a=='launch':answer={'instance':c['instance']}
            elif a=='status':answer=readiness(c,f['observed'],True);answer['observations'][0]['status']['token']=answer['observations'][1]['status']['token']=incoming['token']
            elif a=='arm':answer={'armed':True}
            elif a=='fetch':answer={'files':{},'identity_unchanged':True}
            elif a=='qualify':answer={k:incoming[k] for k in ['transaction','token','instance','host_unknown_sha256']};answer.update(next_action='finish',qualified_boottime_ms=5000)
            else:answer={'finished':True}
            return SimpleNamespace(returncode=0,stdout=json.dumps(answer).encode(),stderr=b'')
        opts=dict(execute=True,window_confirmed=True,ssh=ssh,private=private,require_tests=False)
        with patch.object(controller,'local_inputs',return_value=inputs):
            controller.run('launch',c['transaction'],**opts);root=private/c['transaction']
            check('same transaction launch never repeats load',rejects(lambda:controller.run('launch',c['transaction'],**opts)) and len(calls)==1)
            fail[0]=True;check('status transport failure retained',rejects(lambda:controller.run('status',c['transaction'],**opts)))
            check('read-only failure does not quarantine',not(root/'unknown-private.json').exists())
            fail[0]=False;controller.run('status',c['transaction'],**opts)
            check('same observer status can be rechecked',calls[-1]['action']=='status')
            check('arm requires fresh user-ready flag',rejects(lambda:controller.run('arm',c['transaction'],**opts)))
            fail[0]=True;check('uncertain arm retained',rejects(lambda:controller.run('arm',c['transaction'],user_ready_confirmed=True,**opts)))
            unknown=(root/'unknown-private.json').read_bytes();n=len(calls)
            check('uncertain mutation defaults fetch-only and cannot rearm',rejects(lambda:controller.run('arm',c['transaction'],user_ready_confirmed=True,**opts)) and rejects(lambda:controller.run('status',c['transaction'],**opts)) and len(calls)==n)
            fail[0]=False;controller.run('fetch',c['transaction'],**opts)
            check('fetch performs no cleanup action',calls[-1]['action']=='fetch')
            check('qualification requires explicit terminal review',rejects(lambda:controller.run('qualify',c['transaction'],**opts)))
            controller.run('qualify',c['transaction'],terminal_state_confirmed=True,**opts)
            check('qualification keeps unknown history bound to exact bytes',(root/'unknown-private.json').read_bytes()==unknown and json.loads((root/'qualification-private.json').read_text())['host_unknown_sha256']==common.sha(unknown))
            controller.run('finish',c['transaction'],terminal_state_confirmed=True,**opts)
            check('qualified finish uses a separate one-shot recovery intent',len(list(root.glob('finish-recovery-*-intent-private.json')))==1)
            check('same qualification cannot repeat finish',rejects(lambda:controller.run('finish',c['transaction'],terminal_state_confirmed=True,**opts)))
            common.save(root/'unknown-private.json',{'changed':True});n=len(calls)
            check('changed unknown invalidates qualification before SSH',rejects(lambda:controller.run('finish',c['transaction'],terminal_state_confirmed=True,**opts)) and n==len(calls))

    # Actual remote terminal process gate: never qualify a still-running mutator.
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);common.save(root/'load-process.json',{'pid':99,'start_ticks':1,'argv':['insmod']});rc=dict(c,bundle=str(root))
        with patch.object(common,'process',return_value={'state':'alive'}):check('actual remote qualification blocks live mutator',rejects(lambda:device.mutators_terminal(rc)))
        with patch.object(common,'process',return_value={'state':'zombie'}):check('actual remote qualification accepts joined zombie identity',device.mutators_terminal(rc)['load-process.json']['state']=='zombie')
    compile(controller.BOOTSTRAP,'remote-bootstrap','exec')
    for name in ['common.py','protocol.py','gates.py','device.py','observer.py','controller.py']:
        ast.parse((HERE/name).read_text())
    check('bootstrap and all new runtime Python parse',True)
    # Verify current local pins once, without remote access or requiring circular receipt.
    controller.local_inputs(require_tests=False);check('R7 identity R8 helper and frozen icon local pins match',True)
    files={name:common.sha((HERE/name).read_bytes()) for name in controller.RUNTIME+['controller.py','input-pins.json','helper-protocol.json','test-controller.py']}
    receipt={'passed':True,'scope':'new actual schema/aggregation/readiness/controller/terminal-process boundaries only','cases':cases,'case_count':len(cases),'files':files,'worker_sha256':files['device.py'],'phone_accessed':False,'ssh_executed':False,'sdk_invoked':False,'original_helper_12_groups_rerun':False,'old_icon_matrix_rerun':False,'actual_fixture_functions_sha256':common.sha((AUTHOR/'tested-functions.inc').read_bytes())}
    common.save(HERE/'test-result.json',receipt);print(json.dumps({'passed':True,'case_count':len(cases),'worker_sha256':receipt['worker_sha256']}))

if __name__=='__main__':tests()
