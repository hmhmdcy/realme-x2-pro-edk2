"""Observe real ACK/indication ordering and advertised aid sizes on one LOC client."""
from pathlib import Path
import json,os,traceback
import gi
gi.require_version('Qmi','1.0');gi.require_version('Qrtr','1.0')
from gi.repository import Qmi,Qrtr,GLib

os.umask(0o077);out=Path('/var/lib/samurai/k190-orbit-order');assert not out.exists();out.mkdir(mode=0o700)
loop=GLib.MainLoop();device=None;client=None;bus=None;closing=False;current=None
state=dict(stage=190,requests=[],errors=[])
def save():(out/'summary.json').write_text(json.dumps(state,indent=2)+'\n')
def end():save();loop.quit();return False
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
 if device is not None and client is not None:device.release_client(client,Qmi.DeviceReleaseClientFlags.RELEASE_CID,10,None,released,None)
 elif device is not None:device.close_async(10,None,closed,None)
 else:end()
 return False
def guard(fn):
 def wrapped(*args):
  try:return fn(*args)
  except Exception:state['errors'].append(traceback.format_exc());cleanup()
 return wrapped
def advance():
 if not current.get('ack') or not current.get('indication'):return
 state['requests'].append(current.copy());save()
 if len(state['requests'])==4:cleanup()
 else:GLib.timeout_add(250,send)
@guard
def indication(source,output):
 assert current is not None and not current.get('indication')
 current['events'].append('indication');current['indication']=True;current['status']=int(output.get_indication_status())
 try:current['allowed_sizes']=[int(v) for v in output.get_allowed_sizes()]
 except Exception:current['allowed_sizes']=None
 try:
  servers=output.get_server_list();current['server_count']=len(servers)
  (out/'servers-private.json').write_text(json.dumps(list(servers)))
 except Exception:current['server_count']=0
 advance()
@guard
def acknowledged(source,result,*unused):
 output=source.get_predicted_orbits_data_source_finish(result);output.get_result()
 current['events'].append('ack');current['ack']=True;advance()
def send():
 global current
 current=dict(index=len(state['requests'])+1,events=[],ack=False,indication=False)
 client.get_predicted_orbits_data_source(None,10,None,acknowledged,None);return False
@guard
def allocated(source,result,*unused):
 global client
 client=source.allocate_client_finish(result);client.connect('get-predicted-orbits-data-source',indication);send()
@guard
def opened(source,result,*unused):
 source.open_finish(result);device.allocate_client(Qmi.Service.LOC,Qmi.CID_NONE,10,None,allocated,None)
@guard
def ready(source,result,*unused):
 global device
 device=Qmi.Device.new_from_node_finish(result);device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS,10,None,opened,None)
@guard
def bus_ready(source,result,*unused):
 global bus
 bus=Qrtr.Bus.new_finish(result);node=bus.get_node(0);assert node;Qmi.Device.new_from_node(node,None,ready,None)
def expired():state['deadline']=True;cleanup();return False
GLib.timeout_add_seconds(35,expired);GLib.timeout_add_seconds(58,end)
Qrtr.Bus.new(2000,None,bus_ready,None);loop.run();save();print(json.dumps(state))
assert len(state['requests'])==4 and state.get('client_released') and state.get('device_closed') and not state['errors']
