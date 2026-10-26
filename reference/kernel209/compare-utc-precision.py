from pathlib import Path
import dbus,json,math,os,signal,subprocess,sys,time,traceback
sys.path.insert(0,'/var/lib/samurai/k209-tools')
from loc_nmea import LocSession,await_call,pump_until,Qmi,GLib
from pqwm1 import sentence,decode
from clock_uncertainty import uncertainty
os.umask(0o077)
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k209-baseline/boot-id-private.txt').read_bytes()
out=root/'k209-clock-compare';assert not out.exists();out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0')
props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'));old=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(old['Enabled'])==0 and not bus.name_has_owner('org.freedesktop.GeoClue2')
watch_before=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch_before['running'] and not watch_before['active'] and watch_before['time_prepared']
(out/'watch-before-private.json').write_text(json.dumps(watch_before,indent=2)+'\n')
(out/'location-before-private.json').write_text(json.dumps(old,default=str,indent=2)+'\n')
report=dict(stage=209,single_continuous_mm_gps_session=True,rf_power_firmware_and_assistance_unchanged=True,product_helper_unchanged=True,engine_states=[],utc_exchanges=[],phases={},errors=[])
session=LocSession();original=None;gps_requested=False;precise_sent=False;started=time.monotonic()
beforelog=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(beforelog)
def save():(out/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
def inject(milliseconds,label):
    received=[];handler=session.client.connect('inject-utc-time',lambda _client,output:received.append(output))
    receipt=dict(label=label,uncertainty_ms=milliseconds,ack=False,indication=False)
    stamp=time.monotonic()
    try:
        request=Qmi.MessageLocInjectUtcTimeInput.new()
        request.set_utc_time(GLib.get_real_time()//1000);request.set_time_uncertainty(milliseconds);request.set_time_source(Qmi.LocInjectedTimeSource.UNKNOWN)
        output=await_call(lambda cancel,cb:session.client.inject_utc_time(request,10,cancel,cb,None),lambda source,res:source.inject_utc_time_finish(res))
        output.get_result();receipt['ack']=True
        assert pump_until(lambda:bool(received),12)
        assert len(received)==1;receipt['indication']=True;receipt['status']=int(received[0].get_indication_status());assert receipt['status']==0
    finally:
        receipt['ack_and_completion_elapsed_ms']=(time.monotonic()-stamp)*1000
        session.client.disconnect(handler);report['utc_exchanges'].append(receipt);save()
def capture(name,seconds):
    seen=set();records=[];last=0;deadline=time.monotonic()+seconds
    phase=report['phases'][name]=dict(unique_nmea=0,nmea_types={},checksum_errors=0,pqwm1_reports=0,valid_gga=0,active_rmc=0,positive_cnr_fields=0)
    with (out/(name+'-mm-private.jsonl')).open('x') as stream:
        def done():
            nonlocal last
            now=time.monotonic()
            if now-last<1:return now>=deadline
            last=now;values=api.GetLocation(timeout=8);host_utc_ms=time.time()*1000
            stream.write(json.dumps(dict(host_utc_ms=host_utc_ms,elapsed=now-started,values=values),default=str)+'\n');stream.flush()
            for key,value in values.items():
                if int(key)!=4:continue
                for text in str(value).replace('\r','').split('\n'):
                    if not text.startswith('$') or text in seen:continue
                    seen.add(text);phase['unique_nmea']+=1
                    try:fields=sentence(text)
                    except ValueError:phase['checksum_errors']+=1;continue
                    kind=fields[0];phase['nmea_types'][kind]=phase['nmea_types'].get(kind,0)+1
                    if kind=='PQWM1':records.append(decode(text));phase['pqwm1_reports']+=1
                    if kind.endswith('GGA') and len(fields)>6 and fields[6].isdigit():phase['valid_gga']+=int(int(fields[6])>0)
                    if kind.endswith('RMC') and len(fields)>2:phase['active_rmc']+=int(fields[2]=='A')
                    if kind.endswith('GSV'):
                        for i in range(7,len(fields),4):
                            try:value=float(fields[i])
                            except ValueError:continue
                            phase['positive_cnr_fields']+=int(math.isfinite(value) and value>0)
            if records:
                phase['clock_ranges']={field:dict(min=min(values),max=max(values)) for field in ['time_valid','time_source','time_unc_ns','time_unc','clock_bias_unc','error_recovery'] if (values:=[r[field] for r in records if r[field] is not None])}
            save();return now>=deadline
        assert pump_until(done,seconds+15)
    (out/(name+'-pqwm1-private.json')).write_text(json.dumps(records,indent=2)+'\n')
def interrupted(_signum,_frame):raise RuntimeError('Comparison interrupted')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
try:
    session.open();original=session.nmea_mask();assert original==63
    session.connect('engine-state',lambda _client,output:report['engine_states'].append(int(output.get_engine_state())))
    session.register(int(Qmi.LocEventRegistrationFlag.ENGINE_STATE));session.nmea_mask(original|int(Qmi.LocNmeaType.DEBUG))
    report['debug_mask']=session.nmea_mask();assert report['debug_mask']==131135
    gps_requested=True;api.SetGpsRefreshRate(dbus.UInt32(1),timeout=10);api.Setup(dbus.UInt32(6),dbus.Boolean(True),timeout=30)
    def helper_finished():
        state=json.loads((root/'gnss-assist/watch-state.json').read_text())
        return state['worker_starts']==state['worker_completions']==watch_before['worker_starts']+1
    assert pump_until(helper_finished,25),'Automatic helper has not completed; do not compare overlapping injections'
    capture('fixed1000',25)
    clock_started=time.monotonic();tracking=subprocess.run(['chronyc','-n','tracking'],capture_output=True,text=True,timeout=10,env={**os.environ,'LC_ALL':'C'})
    (out/'chrony-tracking-private.txt').write_text(tracking.stdout+tracking.stderr);assert tracking.returncode==0
    estimate=uncertainty(tracking.stdout,query_age_seconds=time.monotonic()-clock_started)
    report['proposed_clock_bound']=estimate
    precise_sent=True;inject(estimate['uncertainty_ms'],'measured_bound_plus_margin')
    assert report['utc_exchanges'][-1]['ack_and_completion_elapsed_ms']<estimate['transport_margin_ms'],'Transport exceeded declared margin'
    settle=time.monotonic()+3;assert pump_until(lambda:time.monotonic()>=settle,5)
    capture('measured_bound',60)
except Exception as error:
    report['errors'].append(type(error).__name__);(out/'error-private.txt').write_text(traceback.format_exc())
finally:
    try:
        assert str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner
        if precise_sent and session.client is not None:inject(1000,'original_input_policy_fresh_utc')
        if gps_requested:
            api.Setup(dbus.UInt32(0),dbus.Boolean(bool(old['SignalsLocation'])),timeout=30);api.SetGpsRefreshRate(dbus.UInt32(int(old['GpsRefreshRate'])),timeout=10)
        if original is not None and session.client is not None:session.nmea_mask(original);report['nmea_mask_restored']=session.nmea_mask()==original
        report['gps_enabled_final']=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))
    except Exception as error:report['errors'].append('cleanup-'+type(error).__name__);(out/'cleanup-error-private.txt').write_text(traceback.format_exc())
    try:report.update(session.close())
    except Exception as error:report['errors'].append('close-'+type(error).__name__)
    report['mask_receipts']=session.receipts;report['elapsed_seconds']=time.monotonic()-started
    state=json.loads((root/'gnss-assist/watch-state.json').read_text());report['watch_worker_starts']=state['worker_starts'];report['watch_worker_completions']=state['worker_completions']
    (out/'watch-after-private.json').write_text(json.dumps(state,indent=2)+'\n')
    afterlog=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(afterlog)
    report['fault_delta']={name:afterlog.count(word)-beforelog.count(word) for name,word in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
    assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close()
print(json.dumps(report))
