"""Subscribe to SV events of the existing MM session; never start or stop an engine."""
from pathlib import Path
import collections,dbus,json,math,os,traceback
import gi
gi.require_version('Qmi','1.0');gi.require_version('Qrtr','1.0')
from gi.repository import Qmi,Qrtr,GLib
os.umask(0o077);out=Path('/var/lib/samurai/k191-sv-observer-r3');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
db=dbus.SystemBus(private=True);props=dbus.Interface(db.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
enabled=int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));db.close()
state=dict(stage=191,mm_enabled_at_start=enabled,engine_start_sent=False,engine_stop_sent=False,registered=False,events=0,valid_snr_fields=0,positive_snr_fields=0,maximum_snr=None,status_counts={},errors=[])
if enabled&6!=6:
 state['skipped_mm_session_already_finished']=True;(out/'summary.json').write_text(json.dumps(state));print(json.dumps(state));raise SystemExit(0)
snr_names=[n for n in dir(Qmi.LocSatelliteValidInformation) if n.isupper() and ('SIGNAL' in n or 'SNR' in n)];assert len(snr_names)==1
snr_bit=int(getattr(Qmi.LocSatelliteValidInformation,snr_names[0]));loop=GLib.MainLoop();device=client=bus=None;closing=False
def end():(out/'summary.json').write_text(json.dumps(state,indent=2)+'\n');loop.quit();return False
def closed(source,result,*unused):
 try:source.close_finish(result);state['device_closed']=True
 except Exception:state['errors'].append(traceback.format_exc())
 end()
def released(source,result,*unused):
 try:source.release_client_finish(result);state['client_released']=True
 except Exception:state['errors'].append(traceback.format_exc())
 source.close_async(10,None,closed,None)
def cleanup():
 global closing
 if closing:return False
 closing=True
 if client is not None:device.release_client(client,Qmi.DeviceReleaseClientFlags.RELEASE_CID,10,None,released,None)
 elif device is not None:device.close_async(10,None,closed,None)
 else:end()
 return False
def guard(fn):
 def wrapped(*args):
  try:return fn(*args)
  except Exception:state['errors'].append(traceback.format_exc());cleanup()
 return wrapped
@guard
def indication(source,output):
 state['events']+=1
 try:satellites=output.get_list()
 except GLib.Error as error:
  if error.matches(Qmi.core_error_quark(),Qmi.CoreError.TLVNOTFOUND):
   state['events_without_sv_list']=state.get('events_without_sv_list',0)+1;return
  raise
 records=[]
 for sv in satellites:
  status=sv.satellite_status.value_nick;state['status_counts'][status]=state['status_counts'].get(status,0)+1
  snr=float(sv.signal_to_noise_ratio_bhz);valid=bool(int(sv.valid_information)&snr_bit)
  if valid and math.isfinite(snr):
   state['valid_snr_fields']+=1;state['positive_snr_fields']+=int(snr>0);state['maximum_snr']=max(state['maximum_snr'] or 0,snr)
  records.append(dict(id=int(sv.gnss_satellite_id),valid=int(sv.valid_information),status=status,snr=snr))
 with (out/'satellites-private.jsonl').open('a') as stream:stream.write(json.dumps(records)+'\n')
@guard
def registered(source,result,*unused):
 output=source.register_events_finish(result);output.get_result();state['registered']=True;GLib.timeout_add_seconds(15,cleanup)
@guard
def allocated(source,result,*unused):
 global client
 client=source.allocate_client_finish(result);client.connect('gnss-sv-info',indication)
 request=Qmi.MessageLocRegisterEventsInput.new();request.set_event_registration_mask(Qmi.LocEventRegistrationFlag.GNSS_SATELLITE_INFO)
 client.register_events(request,10,None,registered,None)
@guard
def opened(source,result,*unused):source.open_finish(result);source.allocate_client(Qmi.Service.LOC,Qmi.CID_NONE,10,None,allocated,None)
@guard
def ready(source,result,*unused):
 global device
 device=Qmi.Device.new_from_node_finish(result);device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS,10,None,opened,None)
@guard
def bus_ready(source,result,*unused):
 global bus
 bus=Qrtr.Bus.new_finish(result);node=bus.get_node(0);assert node is not None;Qmi.Device.new_from_node(node,None,ready,None)
GLib.timeout_add_seconds(40,cleanup);GLib.timeout_add_seconds(58,end)
Qrtr.Bus.new(2000,None,bus_ready,None);loop.run();end();print(json.dumps(state))
assert state['registered'] and state.get('client_released') and state.get('device_closed') and not state['errors']
