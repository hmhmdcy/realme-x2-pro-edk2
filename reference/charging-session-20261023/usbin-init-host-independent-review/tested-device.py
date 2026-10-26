"""Remote side of one temporary helper transaction. Import performs no action."""
from pathlib import Path
import base64
import json
import os
import signal
import subprocess
import sys
import time
import common
import gates
import observer
import protocol

OWNER=Path('/run/samurai-usbin-init-host-owner.json')
MUTATING={'launch','arm','finish','close-expired'}
def new(path,data):
    with Path(path).open('x') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
def read_json(path):
    try:return json.loads(Path(path).read_text())
    except (OSError,ValueError):return {}
def owned(c):
    o=read_json(OWNER)
    if any(o.get(k)!=c.get(k) for k in ['transaction','token','expected_boot']):raise ValueError('exclusive helper owner differs')
def bundle_check(c):
    for name,digest in c['files'].items():
        p=Path(c['bundle'],name)
        if p.is_symlink() or common.sha(p.read_bytes())!=digest:raise ValueError('uploaded bundle differs')
def command(c,name,argv):
    root=Path(c['bundle']);new(root/(name+'-intent.json'),{'argv':argv,'boottime_ms':common.boot_ms()})
    with (root/(name+'-log.txt')).open('xb') as log:
        child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    stat=Path('/proc',str(child.pid),'stat').read_text();receipt={'pid':child.pid,'start_ticks':int(stat[stat.rindex(')')+2:].split()[19]),'argv':argv}
    new(root/(name+'-process.json'),receipt)
    try:rc=child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        common.save(root/'uncertain.json',{'operation':name,'reason':'child still pending; no kill/retry','process':receipt});raise RuntimeError('module child outcome unknown')
    result={'returncode':rc,'process':receipt};new(root/(name+'-result.json'),result)
    if rc:raise RuntimeError('module command failed; retain raw state')
    return result

def status(c):
    owned(c);common.identity(c);before=read_json(Path(c['bundle'],'environment-before-private.json'))
    same=common.environment()==before;receipt=read_json(Path(c['bundle'],'observer-process.json'));rows=[]
    for index in range(2):
        if index:time.sleep(2.2)
        rows.append({'status':read_json(Path(c['capture'],'status.json')),'process':common.process(receipt),
            'helper':observer.helper(c['instance']),'remote_realtime':time.time(),'remote_boottime_ms':common.boot_ms()})
    return {'observations':rows,'observer_receipt':receipt,'identity_unchanged':True,'environment_unchanged':same,
            'uncertain':Path(c['bundle'],'uncertain.json').exists()}

def stop_observer(c):
    receipt=read_json(Path(c['bundle'],'observer-process.json'));state=common.process(receipt)
    if state['state']=='alive':
        os.kill(receipt['pid'],signal.SIGTERM)
        for _ in range(30):
            time.sleep(.1);state=common.process(receipt)
            if state['state'] in ['absent','zombie']:break
    if state['state'] not in ['absent','zombie']:raise ValueError('observer exit unproved; no module cleanup')
    return state

def observer_terminal(c):
    root=Path(c['bundle']);p=common.process(read_json(root/'observer-process.json'))
    status=read_json(Path(c['capture'],'status.json'));raw=read_json(Path(c['capture'],'capture-private.json'))
    if p['state'] not in ['absent','zombie'] or status.get('terminal') is not True or status.get('active') is not False or any(status.get(k)!=c[k] for k in ['transaction','token']):raise ValueError('exact observer terminal unproved')
    monitor=raw.get('monitor',{})
    if monitor.get('started') is not True or monitor.get('errors')!=[] or type(monitor.get('dbus_returncode')) is not int:raise ValueError('monitor cleanup unproved')
    return read_json(Path(c['capture'],'result.json'))

def success_evidence(c):
    result=observer_terminal(c)
    if not all(result.get(k) is True for k in ['initialization_verified','physical_cycle_passed','environment_unchanged','post_online_telemetry_healthy','cv_cap_preserved']):raise ValueError('physical/init/current evidence incomplete')
    if result.get('helper_terminal',{}).get('instance')!=c['instance']:raise ValueError('capture helper instance differs')
    if common.environment()!=read_json(Path(c['bundle'],'environment-before-private.json')):raise ValueError('fresh environment changed')
    fresh=common.current_sample()
    if not common.healthy(fresh) or fresh['source']['charger']['constant_charge_voltage']>result['source_before']['charger']['constant_charge_voltage']:raise ValueError('fresh protection/CV/source not healthy')
    return result

def mutators_terminal(c):
    rows={}
    for p in Path(c['bundle']).glob('*-process.json'):
        selected=p.name.startswith(('load-','unload-')) or any(p.name.startswith('control-'+a+'-') for a in MUTATING)
        if not selected:continue
        receipt=read_json(p)
        if receipt.get('pid')==os.getpid():continue
        state=common.process(receipt);rows[p.name]=state
        if state['state'] not in ['absent','zombie']:raise ValueError('mutating process not terminal: '+p.name)
    if not (Path(c['bundle'])/'load-process.json').exists():raise ValueError('original load process identity missing')
    return rows

def uncertain_hash(root):
    p=Path(root)/'uncertain.json';return common.sha(p.read_bytes()) if p.exists() else None

def qualification(c,incoming):
    if not incoming.get('terminal_state_confirmed'):raise ValueError('explicit terminal evidence review required')
    root=Path(c['bundle']);processes=mutators_terminal(c);observer_terminal(c)
    if not c.get('instance'):raise ValueError('exact retained helper instance unavailable')
    if common.environment()!=read_json(root/'environment-before-private.json'):raise ValueError('fresh environment changed')
    present=Path('/sys/module',protocol.MODULE).exists()
    if present:
        owned(c);h=observer.helper(c['instance'])
        if not h['fresh']:raise ValueError('helper current read stale')
        s=h['state']
        if protocol.verified(s) or protocol.committed(s):success_evidence(c);next_action='finish'
        elif protocol.close_zero_write(s):next_action='close-expired'
        else:raise ValueError('helper has no qualified terminal outcome')
    else:
        h=read_json(root/'commit-result.json')
        # Recovery commit receipts also remain bound to the exact instance.
        if not h:
            candidates=sorted(root.glob('commit-recovery-*-result.json'));h=read_json(candidates[-1]) if candidates else {}
        committed=bool(h.get('state') and protocol.committed(protocol.parse(h['state'],c['instance'])))
        expired=read_json(root/'close-expired-intent.json')
        if not expired:
            candidates=sorted(root.glob('close-expired-recovery-*-intent.json'));expired=read_json(candidates[-1]) if candidates else {}
        expired=bool(expired.get('state') and protocol.close_zero_write(protocol.parse(expired['state'],c['instance'])))
        if not(committed or expired):raise ValueError('absent module without exact committed or zero-write expiry receipt')
        if not list(root.glob('unload*-process.json')):raise ValueError('absent module lacks original unload process proof')
        if committed:success_evidence(c)
        next_action='finish' if committed else 'close-expired'
        if OWNER.exists():owned(c)
    proof={'transaction':c['transaction'],'token':c['token'],'instance':c['instance'],'next_action':next_action,
        'source_uncertain_sha256':uncertain_hash(root),'host_unknown_sha256':incoming.get('host_unknown_sha256'),
        'module_already_absent':not present,'processes':processes,'qualified_boottime_ms':common.boot_ms()}
    new(root/('qualification-'+str(time.time_ns())+'.json'),proof);common.save(root/'qualification.json',proof)
    return proof

def recovery_proof(c,incoming,action):
    root=Path(c['bundle']);proof=read_json(root/'qualification.json')
    if not(unknown:=incoming.get('host_unknown_sha256')) and not Path(root/'uncertain.json').exists():return None
    if any(proof.get(k)!=c[k] for k in ['transaction','token','instance']) or proof.get('next_action')!=action or proof.get('host_unknown_sha256')!=unknown or proof.get('source_uncertain_sha256')!=uncertain_hash(root):raise ValueError('unknown operation not qualified from exact evidence')
    if not 0<=common.boot_ms()-proof['qualified_boottime_ms']<=30000:raise ValueError('qualification stale')
    mutators_terminal(c);return proof

def execute(action,incoming):
    root=Path(incoming['bundle']);c=read_json(root/'request-private.json')
    if any(c.get(k)!=incoming.get(k) for k in ['transaction','token','expected_boot']):raise ValueError('retained transaction differs')
    bundle_check(c)
    ownstat=Path('/proc/self/stat').read_text()
    new(root/('control-'+action+'-'+str(os.getpid())+'-process.json'),{'pid':os.getpid(),'start_ticks':int(ownstat[ownstat.rindex(')')+2:].split()[19]),
        'argv':[x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(bytes([0])) if x]})
    if action=='launch':
        common.identity(c);c['board']=common.identity(c)['board'];before=common.environment()
        if OWNER.exists() or Path('/sys/module',protocol.MODULE).exists() or Path(protocol.SYSFS).exists():raise ValueError('another helper/owner exists')
        new(OWNER,{k:c[k] for k in ['transaction','token','expected_boot']})
        new(root/'environment-before-private.json',before)
        config=dict(c,execute=True,window_confirmed=True);new(root/'observer-config.json',config)
        argv=['python3','-B',str(root/'observer.py'),'--config',str(root/'observer-config.json')]
        with (root/'observer-log.txt').open('xb') as log:child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        stat=Path('/proc',str(child.pid),'stat').read_text();receipt={'pid':child.pid,'start_ticks':int(stat[stat.rindex(')')+2:].split()[19]),'argv':argv}
        new(root/'observer-process.json',receipt)
        command(c,'load',['insmod',str(root/'samurai-usbin-init.ko'),'register_board=1'])
        common.identity(c);h=observer.helper()
        if not(h['fresh'] and h['state'] and protocol.observed(h['state'])):raise ValueError('new helper not observe-only')
        c['instance']=h['state']['instance'];common.save(root/'request-private.json',c)
        return {'loaded_observe_only':True,'instance':c['instance'],'observer_receipt':receipt,'board':c['board']}
    bundle_check(c);common.identity(c)
    if action=='qualify':return qualification(c,incoming)
    # A prior unload may already have completed; do not try it a second time.
    proof=recovery_proof(c,incoming,action) if action in ['finish','close-expired'] else None
    if action in ['finish','close-expired'] and proof and proof['module_already_absent']:
        if Path('/sys/module',protocol.MODULE).exists() or Path(protocol.SYSFS).exists():raise ValueError('module reappeared after qualification')
        if action=='finish':success_evidence(c)
        else:observer_terminal(c)
        if OWNER.exists():owned(c);OWNER.unlink()
        result={'finished':True,'action':action,'module_absent':True,'owner_released':True,'no_repeated_unload':True,**{k:c[k] for k in ['transaction','token','instance']}}
        new(root/('finish-confirmed-'+str(time.time_ns())+'.json'),result);return result
    owned(c)
    if action=='status':return status(c)
    if Path(root,'uncertain.json').exists() and not proof:raise ValueError('unknown transaction; fetch or explicit qualification only')
    if action=='arm':
        if not incoming.get('user_ready_confirmed'):raise ValueError('root must freshly confirm user readiness')
        data=status(c);gate=gates.ready(data,c,True)
        if not gate['ready_to_arm']:raise ValueError('arm preflight: '+str(gate['reasons']))
        new(root/'arm-intent.json',{'instance':c['instance'],'user_ready_confirmed':True,'boottime_ms':common.boot_ms()})
        with Path(protocol.SYSFS,'control').open('wb',buffering=0) as f:
            if f.write(b'arm\n')!=4:raise RuntimeError('short arm write')
        h=observer.helper(c['instance']);new(root/'arm-result.json',h)
        if not(h['fresh'] and protocol.waiting(h['state'],common.boot_ms())):raise ValueError('arm outcome not known waiting')
        return {'armed':True,'helper':h,'may_prompt_user':False,'next':'status requires two fresh ticks before physical prompt'}
    if action=='finish':
        if not incoming.get('terminal_state_confirmed'):raise ValueError('explicit reviewed completion required')
        h=observer.helper(c['instance']);success_evidence(c)
        if not(h['fresh'] and (protocol.verified(h['state']) or protocol.committed(h['state']))):raise ValueError('completion state insufficient')
        suffix='-recovery-'+str(proof['qualified_boottime_ms']) if proof else ''
        if not protocol.committed(h['state']):
            new(root/('commit'+suffix+'-intent.json'),{'instance':c['instance'],'state':h})
            with Path(protocol.SYSFS,'control').open('wb',buffering=0) as f:
                if f.write(b'commit\n')!=7:raise RuntimeError('short commit write')
            h=observer.helper(c['instance']);new(root/('commit'+suffix+'-result.json'),h)
        if not(h['fresh'] and protocol.committed(h['state'])):raise ValueError('commit/unload authorization unproved')
    elif action=='close-expired':
        if not incoming.get('terminal_state_confirmed'):raise ValueError('expired zero-write state requires explicit confirmation')
        h=observer.helper(c['instance'])
        if not(h['fresh'] and protocol.close_zero_write(h['state'])):raise ValueError('not a confirmed unarmed observe or zero-write expiry')
        new(root/('close-expired'+('-recovery-'+str(proof['qualified_boottime_ms']) if proof else '')+'-intent.json'),h);stop_observer(c);observer_terminal(c)
    else:raise ValueError('unsupported action')
    # No finally unload. Recheck the same instance and exact can_unload gate.
    h=observer.helper(c['instance'])
    if not(h['fresh'] and h['state']['can_unload'] and not h['state']['unknown_write']):raise ValueError('final unload gate closed')
    command(c,'unload'+('-recovery-'+str(proof['qualified_boottime_ms']) if proof else ''),['rmmod',protocol.MODULE])
    if Path('/sys/module',protocol.MODULE).exists() or Path(protocol.SYSFS).exists():raise ValueError('helper removal not proved')
    common.identity(c);owned(c);OWNER.unlink()
    result={'finished':True,'action':action,'module_absent':True,'owner_released':True,**{k:c[k] for k in ['transaction','token','instance']}};new(root/('finish-result-'+str(time.time_ns())+'.json'),result);return result

def main():
    data=json.load(sys.stdin);action=data['action']
    try:response=execute(action,data);print(json.dumps(response));return 0
    except BaseException as e:
        root=Path(data['bundle']);uncertain=action in MUTATING
        failure={'operation':action,'error':type(e).__name__,'message':str(e)}
        new(root/(('mutating-error-' if uncertain else 'read-error-')+action+'-'+str(time.time_ns())+'.json'),failure)
        if uncertain:common.save(root/'uncertain.json',failure)
        print(json.dumps({'operation_unknown':uncertain,'action':action,'error':str(e),'fetch_only':uncertain}));return 1

if __name__=='__main__':raise SystemExit(main())
