"""Run one bounded transient LOC comparison; preserve raw packets privately."""
from pathlib import Path
import dbus,hashlib,json,os,subprocess,sys,time,traceback
os.umask(0o077)
root=Path('/var/lib/samurai');tools=root/'k241-loc-tools';out=root/'k241-loc-differential'
assert not out.exists();out.mkdir(mode=0o700)
state=dict(stage=241,state='preflight',phase='preflight',terminal=False,pid=os.getpid())
def save():
    p=out/'state-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(out/'state-private.json')
save();process=None;bus=None
try:
    boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert boot==(root/'k236-runtime/boot-id-private.txt').read_bytes()
    build=json.loads((tools/'build-summary.json').read_text());binary=tools/'loc-differential'
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256']
    sys.path.insert(0,str(tools));from loc_decode import summarize,regression
    regression()
    bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'))
    objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
    paths=[str(p) for p,v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v];assert len(paths)==1
    props=dbus.Interface(bus.get_object(owner,paths[0]),'org.freedesktop.DBus.Properties')
    before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
    assert int(before['Enabled'])==0 and not before['SignalsLocation']
    assert not bus.name_has_owner('org.freedesktop.GeoClue2')
    watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert not watch['active']
    db=Path('/lib/apk/db/installed').read_bytes();dmesg=subprocess.check_output(['dmesg'])
    (out/'dmesg-before-private.txt').write_bytes(dmesg)
    env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
    with (out/'events-private.jsonl').open('xb') as stdout,(out/'stderr-private.txt').open('xb') as stderr:
        process=subprocess.Popen([str(binary),'high'],stdout=stdout,stderr=stderr,env=env)
        state.update(state='running',phase='differential',child_pid=process.pid);save()
        try:exit_code=process.wait(timeout=470)
        except subprocess.TimeoutExpired:
            state.update(state='termination-requested');save();process.terminate()
            try:exit_code=process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                state.update(state='cleanup-unresolved');save();raise RuntimeError('Inspect active LOC process before another operation')
    records=[json.loads(line) for line in (out/'events-private.jsonl').read_text().splitlines()]
    closed=records[-1];assert closed['kind']=='cleanup'
    markers=[i for i,row in enumerate(records) if row['kind']=='phase'];phases=[]
    for number,start in enumerate(markers):
        end=markers[number+1] if number+1<len(markers) else len(records)
        part=records[start:end];summary=summarize(part)
        summary.update(name=records[start]['name'],configuration_applied=records[start].get('applied'),
            elapsed_start_us=records[start]['elapsed_us'],
            elapsed_end_us=records[end]['elapsed_us'] if end<len(records) else part[-1].get('elapsed_us'),
            measurement_events=sum(row.get('message_id')==0x86 and row['kind']=='indication' for row in part))
        phases.append(summary)
    after=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
    watchafter=json.loads((root/'gnss-assist/watch-state.json').read_text())
    afterlog=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(afterlog)
    report=dict(stage=241,program_exit=exit_code,cleanup=closed,phases=phases,
        commands=summarize(records)['commands'],
        mm_preserved=str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner and all(before[k]==after[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate']),
        assist_idle_preserved=not watchafter['active'] and all(watch[k]==watchafter[k] for k in ['worker_starts','worker_completions']),
        package_database_preserved=db==Path('/lib/apk/db/installed').read_bytes(),
        same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        fault_delta={k:afterlog.count(v)-dmesg.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},
        inherited_aiding_not_reinjected=True,environment='indoor window, user confirmed',no_nv_or_lock_set=True,
        vendor_code_executed=False,incremental_order_not_randomized=True)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    assert exit_code==0 and closed['start_ack'] and closed['stop_ack'] and closed['client_released'] and closed['device_closed']
    assert report['mm_preserved'] and report['assist_idle_preserved'] and report['package_database_preserved'] and report['same_boot']
    assert report['taint']==0 and not any(report['fault_delta'].values())
    assert len(phases)==4 and all(not item['decode_errors'] for item in phases)
    state.update(state='terminal',terminal=True,exit_code=0,cleanup_verified=True);save()
except BaseException:
    (out/'failure-private.txt').write_text(traceback.format_exc())
    state.update(state='failed',terminal=process is None or process.poll() is not None,exit_code=1);save()
    raise
finally:
    if bus is not None:bus.close()
