from pathlib import Path
import dbus,json,os,subprocess,time,signal,traceback
os.umask(0o077)
root=Path('/var/lib/samurai');out=root/'k258-tools'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k257-runtime/boot-id-private.txt').read_bytes()
state=dict(stage=258,phase='preparing',pid=os.getpid(),started_unix=time.time(),power_restored=False)
def save():
    t=out/'status.tmp';t.write_text(json.dumps(state,indent=2));t.replace(out/'status.json')
def query(name,option):
    r=subprocess.run(['qmicli','-p','-d','qrtr://0',option],capture_output=True,timeout=18)
    (out/(name+'-private.log')).write_bytes(r.stdout+r.stderr)
    assert r.returncode==0,'GET query failed: '+name
    return r.stdout.decode()
b=None;props=None;modem=None;before=None;child=None
save()
try:
    b=dbus.SystemBus(private=True)
    owner='org.freedesktop.ModemManager1';iface=owner+'.Modem';li=iface+'.Location'
    objects=dbus.Interface(b.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
    path=next(p for p,v in objects.items() if iface in v);v=objects[path]
    assert str(v[iface]['Sim'])=='/' and int(v[li]['Enabled'])==0 and not bool(v[li]['SignalsLocation'])
    watch=json.loads((root/'gnss-assist/watch-state.json').read_text())
    assert not watch['active'] and watch['time_prepared']
    assert int(Path('/proc/sys/kernel/tainted').read_text())==0
    assert (Path('/sys/class/power_supply/mp2650-input/online').read_text().strip())=='0'
    obj=b.get_object(owner,path);props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');modem=dbus.Interface(obj,iface)
    before=int(props.Get(iface,'PowerState'));state['power_before']=before
    state['dms_before_online']='online' in query('dms-before','--dms-get-operating-mode').lower()
    save()
    if before!=3:modem.SetPowerState(dbus.UInt32(3),timeout=30)
    state['power_during']=int(props.Get(iface,'PowerState'));assert state['power_during']==3
    state['dms_during_online']="'online'" in query('dms-during','--dms-get-operating-mode').lower()
    assert state['dms_during_online'],'DMS readback not online'
    query('loc-operation','--loc-get-operation-mode');query('loc-lock','--loc-get-engine-lock')
    state.update(phase='observing',observation_launched_unix=time.time());save()
    with (out/'events-private.jsonl').open('wb') as log,(out/'client-stderr-private.log').open('wb') as err:
        child=subprocess.Popen([str(out/'loc-session'),'high'],stdin=subprocess.DEVNULL,stdout=log,stderr=err,start_new_session=True)
        state['client_pid']=child.pid;save()
        try:rc=child.wait(timeout=365)
        except subprocess.TimeoutExpired:
            state['client_timeout']=True;child.send_signal(signal.SIGTERM)
            try:rc=child.wait(timeout=55)
            except subprocess.TimeoutExpired:child.kill();rc=child.wait(timeout=5)
        state['client_returncode']=rc
    state['phase']='restoring';save()
except BaseException as e:
    (out/'worker-error-private.log').write_text(traceback.format_exc())
    state['error_type']=type(e).__name__
finally:
    if child is not None and child.poll() is None:
        child.send_signal(signal.SIGTERM)
        try:child.wait(timeout=55)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
    if props is not None and before is not None:
        try:
            if int(props.Get(iface,'PowerState'))!=before:modem.SetPowerState(dbus.UInt32(before),timeout=30)
            state['power_after']=int(props.Get(iface,'PowerState'))
            state['power_restored']=state['power_after']==before
            state['dms_after_online']="'online'" in query('dms-after','--dms-get-operating-mode').lower()
        except BaseException as e:state['restore_error_type']=type(e).__name__
    state['taint_after']=int(Path('/proc/sys/kernel/tainted').read_text())
    if b is not None:b.close()
    state.update(phase='complete',finished_unix=time.time());save()
