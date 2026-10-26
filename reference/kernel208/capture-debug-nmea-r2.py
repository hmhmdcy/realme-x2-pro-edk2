from pathlib import Path
import collections,dbus,hashlib,json,math,os,signal,subprocess,sys,time,traceback
sys.path.insert(0,'/var/lib/samurai/k208-loc-tools')
from loc_nmea import LocSession,pump_until,Qmi,GLib
from pqwm1 import decode,sentence
os.umask(0o077)
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k208-baseline/boot-id-private.txt').read_bytes()
out=root/'k208-debug-nmea-r2';assert not out.exists();out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
bus=dbus.SystemBus(private=True)
obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0')
props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'))
old=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(old['Enabled'])==0 and not bus.name_has_owner('org.freedesktop.GeoClue2')
(out/'location-before-private.json').write_text(json.dumps(old,default=str,indent=2)+'\n')
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['time_prepared']
(out/'watch-before-private.json').write_text(json.dumps(watch,indent=2)+'\n')
beforelog=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(beforelog)
session=LocSession();original=None;gps_requested=False;seen=set();records=[];last_progress=0
report=dict(stage=208,debug_nmea_temporary=True,mm_used_to_control_gps=True,loc_engine_start_sent=False,loc_engine_stop_sent=False,
    power_state_changed=False,modem_restarted=False,nmea_messages=0,nmea_sentences=0,nmea_types={},checksum_errors=0,pqwm1_reports=0,pqwm1_parse_errors=0,positive_cnr_fields=0,valid_gga=0,engine_states=[],fix_session_states=[],errors=[])
def save():
    (out/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
def receive(_client,output):
    try:
        raw=str(output.get_nmea_string());report['nmea_messages']+=1
        with (out/'nmea-private.jsonl').open('a') as stream:stream.write(json.dumps(dict(elapsed=time.monotonic()-started,nmea=raw))+'\n')
        for text in raw.replace('\r','').split('\n'):
            if not text.startswith('$') or text in seen:continue
            seen.add(text);report['nmea_sentences']+=1
            try:fields=sentence(text)
            except ValueError:report['checksum_errors']+=1;continue
            name=fields[0];report['nmea_types'][name]=report['nmea_types'].get(name,0)+1
            if name=='PQWM1':
                try:
                    record=decode(text);records.append(record);report['pqwm1_reports']+=1
                    with (out/'pqwm1-private.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
                except ValueError:report['pqwm1_parse_errors']+=1
            if name.endswith('GGA') and len(fields)>6 and fields[6].isdigit():report['valid_gga']+=int(int(fields[6])>0)
            if name.endswith('GSV'):
                for index in range(7,len(fields),4):
                    try:value=float(fields[index])
                    except ValueError:continue
                    report['positive_cnr_fields']+=int(math.isfinite(value) and value>0)
    except Exception as error:
        report['errors'].append(type(error).__name__)
        with (out/'callback-errors-private.txt').open('a') as stream:stream.write(traceback.format_exc())
def engine(_client,output):
    try:report['engine_states'].append(int(output.get_engine_state()))
    except Exception as error:report['errors'].append(type(error).__name__)
def fix_session(_client,output):
    try:report['fix_session_states'].append(int(output.get_session_state()))
    except Exception as error:report['errors'].append(type(error).__name__)
def terminate(_signum,_frame):raise RuntimeError('Diagnostic interrupted; cleanup required')
signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
started=time.monotonic()
try:
    session.open();original=session.nmea_mask();report['original_nmea_mask']=original
    (out/'original-nmea-mask-private.json').write_text(json.dumps(dict(mask=original))+'\n')
    session.connect('nmea',receive);session.connect('engine-state',engine)
    session.register(int(Qmi.LocEventRegistrationFlag.NMEA|Qmi.LocEventRegistrationFlag.ENGINE_STATE))
    session.nmea_mask(original|int(Qmi.LocNmeaType.DEBUG))
    report['temporary_nmea_mask']=session.nmea_mask();assert report['temporary_nmea_mask']==original|int(Qmi.LocNmeaType.DEBUG)
    gps_requested=True
    api.SetGpsRefreshRate(dbus.UInt32(1),timeout=10)
    api.Setup(dbus.UInt32(6),dbus.Boolean(True),timeout=30)
    report['gps_enabled_during_capture']=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))
    assert report['gps_enabled_during_capture']&6==6
    report['mask_after_mm_start']=session.nmea_mask();assert report['mask_after_mm_start']&int(Qmi.LocNmeaType.DEBUG)
    deadline=time.monotonic()+120
    def completed():
        global last_progress
        now=time.monotonic()
        if now-last_progress>=3:save();last_progress=now
        return now>=deadline
    assert pump_until(completed,125)
except Exception as error:
    report['errors'].append(type(error).__name__)
    (out/'worker-error-private.txt').write_text(traceback.format_exc())
finally:
    try:
        assert str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner
        if gps_requested:
            api.Setup(dbus.UInt32(0),dbus.Boolean(bool(old['SignalsLocation'])),timeout=30)
            api.SetGpsRefreshRate(dbus.UInt32(int(old['GpsRefreshRate'])),timeout=10)
        if original is not None and session.client is not None:
            report['mask_before_restore']=session.nmea_mask()
            session.nmea_mask(original)
            report['nmea_mask_restored']=session.nmea_mask()==original
        report['gps_enabled_final']=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))
    except Exception as error:
        report['errors'].append('cleanup-'+type(error).__name__)
        (out/'cleanup-error-private.txt').write_text(traceback.format_exc())
    try:report.update(session.close())
    except Exception as error:report['errors'].append('close-'+type(error).__name__)
    report['receipts']=session.receipts
    report['elapsed_seconds']=time.monotonic()-started
    watch=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-after-private.json').write_text(json.dumps(watch,indent=2)+'\n')
    report['watch_worker_starts']=watch['worker_starts'];report['watch_worker_completions']=watch['worker_completions']
    afterlog=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(afterlog)
    report['fault_delta']={k:afterlog.count(v)-beforelog.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
    if records:
        report['rf_clock_ranges']={name:dict(min=min(values),max=max(values),samples=len(values)) for name in ['time_valid','time_source','time_unc','clock_bias','clock_bias_unc','xo_state','pga_gain','gps_bp_i','gps_bp_q','adc_i','adc_q','jammer_gps','jammer_glo','jammer_bds','jammer_gal','error_recovery','agc_gps','agc_glo','agc_bds','agc_gal'] if (values:=[record[name] for record in records if record[name] is not None])}
    assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close()
print(json.dumps(report))
