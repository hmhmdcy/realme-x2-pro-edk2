"""Inject synchronized UTC once and require the separate completion indication."""
from pathlib import Path
import collections,json,os,time,traceback
import gi
gi.require_version('Qmi','1.0');gi.require_version('Qrtr','1.0')
from gi.repository import Qmi,Qrtr,GLib

os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k201-baseline/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k201-utc-injection');assert not out.exists();out.mkdir(mode=0o700)
import subprocess
tracking=subprocess.check_output(['chronyc','tracking']);assert b'Leap status     : Normal' in tracking
(out/'chrony-private.txt').write_bytes(tracking)
loop=GLib.MainLoop();device=None;client=None;bus=None;closing=False
state=dict(stage=201,single_injection_sent=False,request_ack=False,completion_indication=False,
 uncertainty_ms=1000,clock_synchronized=True,engine_start_sent=False,errors=[])
def save(): (out/'summary.json').write_text(json.dumps(state,indent=2)+'\n')
def end():save();loop.quit();return False
def closed(source,result,*args):
 try:source.close_finish(result);state['device_closed']=True
 except Exception:state['errors'].append(traceback.format_exc())
 end()
def released(source,result,*args):
 try:source.release_client_finish(result);state['client_released']=True
 except Exception:state['errors'].append(traceback.format_exc())
 source.close_async(10,None,closed,None)
def cleanup():
 global closing
 if closing:return False
 closing=True
 if device is not None and client is not None:device.release_client(client,Qmi.DeviceReleaseClientFlags.RELEASE_CID,10,None,released,None)
 elif device is not None:device.close_async(10,None,closed,None)
 else:end()
 return False
def guard(fn):
 def wrapped(*args):
  try:return fn(*args)
  except Exception:state['errors'].append(traceback.format_exc());cleanup()
 return wrapped
def maybe_finish():
 if state['request_ack'] and state['completion_indication']:cleanup()
@guard
def indication(source,output):
 status=output.get_indication_status();state['indication_status']=int(status)
 state['completion_indication']=int(status)==int(Qmi.LocIndicationStatus.SUCCESS)
 assert state['completion_indication'];maybe_finish()
@guard
def injected(source,result,*args):
 output=source.inject_utc_time_finish(result);output.get_result();state['request_ack']=True;maybe_finish()
@guard
def allocated(source,result,*args):
 global client
 client=source.allocate_client_finish(result);client.connect('inject-utc-time',indication)
 request=Qmi.MessageLocInjectUtcTimeInput.new();request.set_utc_time(GLib.get_real_time()//1000)
 request.set_time_uncertainty(1000);request.set_time_source(Qmi.LocInjectedTimeSource.UNKNOWN)
 state['single_injection_sent']=True;save();client.inject_utc_time(request,10,None,injected,None)
@guard
def opened(source,result,*args):
 source.open_finish(result);source.allocate_client(Qmi.Service.LOC,Qmi.CID_NONE,10,None,allocated,None)
@guard
def ready(source,result,*args):
 global device
 device=Qmi.Device.new_from_node_finish(result);device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS,10,None,opened,None)
@guard
def bus_ready(source,result,*args):
 global bus
 bus=Qrtr.Bus.new_finish(result);node=bus.get_node(0);assert node is not None;Qmi.Device.new_from_node(node,None,ready,None)
def expired():state['deadline']=True;cleanup();return False
GLib.timeout_add_seconds(35,expired);GLib.timeout_add_seconds(58,end)
Qrtr.Bus.new(2000,None,bus_ready,None);loop.run();save();print(json.dumps(state))
raise SystemExit(0 if state['request_ack'] and state['completion_indication'] and state.get('client_released') and state.get('device_closed') and not state['errors'] else 1)
