"""Read firmware-reported orbit validity on one temporary LOC client."""
from pathlib import Path
import json,os,sys,traceback
import gi
gi.require_version('Qmi','1.0');gi.require_version('Qrtr','1.0')
from gi.repository import Qmi,Qrtr,GLib
os.umask(0o077)
phase=sys.argv[1];assert phase in ['before','before-r2','after']
out=Path('/var/lib/samurai/k201-validity-'+phase);out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k201-baseline/boot-id-private.txt').read_bytes()
loop=GLib.MainLoop();device=client=bus=None;closing=False
state=dict(stage=201,phase=phase,events=[],ack=False,indication=False,errors=[],engine_start_sent=False)
def end():(out/'summary.json').write_text(json.dumps(state,indent=2)+'\n');loop.quit();return False
def closed(source,result,*unused):
 try:assert source.close_finish(result);state['device_closed']=True
 except Exception:state['errors'].append(traceback.format_exc())
 end()
def released(source,result,*unused):
 try:assert source.release_client_finish(result);state['client_released']=True
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
def advance():
 if state['ack'] and state['indication']:cleanup()
@guard
def indication(source,output):
 state['events'].append('indication');state['status']=int(output.get_indication_status());assert state['status']==0
 values=output.get_validity_info();state['start_utc_timestamp']=int(values[0]);state['duration_hours']=int(values[1]);state['indication']=True;advance()
@guard
def acknowledged(source,result,*unused):
 output=source.get_predicted_orbits_data_validity_finish(result);output.get_result();state['events'].append('ack');state['ack']=True;advance()
@guard
def allocated(source,result,*unused):
 global client
 client=source.allocate_client_finish(result);client.connect('get-predicted-orbits-data-validity',indication)
 client.get_predicted_orbits_data_validity(None,10,None,acknowledged,None)
@guard
def opened(source,result,*unused):
 assert source.open_finish(result);source.allocate_client(Qmi.Service.LOC,Qmi.CID_NONE,10,None,allocated,None)
@guard
def ready(source,result,*unused):
 global device
 device=Qmi.Device.new_from_node_finish(result);device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS,10,None,opened,None)
@guard
def bus_ready(source,result,*unused):
 global bus
 bus=Qrtr.Bus.new_finish(result);node=bus.get_node(0);assert node is not None;Qmi.Device.new_from_node(node,None,ready,None)
def expired():state['deadline']=True;cleanup();return False
GLib.timeout_add_seconds(35,expired);GLib.timeout_add_seconds(58,end)
Qrtr.Bus.new(2000,None,bus_ready,None);loop.run();end();print(json.dumps(state))
assert state['ack'] and state['indication'] and state.get('client_released') and state.get('device_closed') and not state['errors']
