"""One LOC client registers indications, starts, observes and stops its session."""
from pathlib import Path
import collections, json, os, time, traceback
import gi
gi.require_version('Qmi','1.0')
gi.require_version('Qrtr','1.0')
from gi.repository import Qmi,Qrtr,GLib

dest=Path('/var/lib/samurai/k114-gnss-single-client')
assert not dest.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_text()==Path('/var/lib/samurai/k114-rootfs-export/boot-id-private.txt').read_text()
dest.mkdir(mode=0o700)
os.umask(0o077)
state={'session_id':115,'client_registered':False,'start_ack':False,'stop_ack':False,'events':collections.Counter(),'errors':[]}
loop=GLib.MainLoop()
client=None
device=None
bus=None
stopping=False
def write_state():
    (dest/'state-private.json').write_text(json.dumps(state,indent=2,default=str)+'\n')
def fail():
    state['errors'].append(traceback.format_exc())
    write_state()
    stop()
def cb(fn):
    def wrapped(*args):
        try: fn(*args)
        except Exception: fail()
    return wrapped
def stop():
    global stopping
    if stopping: return False
    stopping=True
    if client is None or not state['start_ack']:
        write_state(); loop.quit(); return False
    request=Qmi.MessageLocStopInput.new()
    request.set_session_id(115)
    client.stop(request,10,None,stop_done,None)
    GLib.timeout_add_seconds(15,hard_end)
    return False
def hard_end():
    state['deadline_exit']=True
    write_state(); loop.quit(); return False
@cb
def stop_done(source,result,*args):
    output=source.stop_finish(result)
    state['stop_ack']=bool(output.get_result())
    write_state(); loop.quit()
def on_event(source,output,name):
    state['events'][name]+=1
    values={}
    for method in dir(output):
        if not method.startswith('get_'): continue
        try: values[method]=repr(getattr(output,method)())
        except Exception as error: values[method]=str(error)
    with (dest/'events-private.jsonl').open('a') as f:
        f.write(json.dumps(dict(monotonic=time.monotonic(),signal=name,values=values))+'\n')
    write_state()
@cb
def start_done(source,result,*args):
    output=source.start_finish(result)
    state['start_ack']=bool(output.get_result())
    write_state()
    GLib.timeout_add_seconds(55,stop)
@cb
def registered(source,result,*args):
    output=source.register_events_finish(result)
    state['client_registered']=bool(output.get_result())
    request=Qmi.MessageLocStartInput.new()
    request.set_session_id(115)
    request.set_fix_recurrence_type(Qmi.LocFixRecurrenceType.PERIODIC)
    request.set_intermediate_report_state(Qmi.LocIntermediateReportState.ENABLE)
    request.set_minimum_interval_between_position_reports(1000)
    state['start_request_sent']=True
    write_state()
    client.start(request,10,None,start_done,None)
@cb
def allocated(source,result,*args):
    global client
    client=source.allocate_client_finish(result)
    for name in ['position-report','gnss-sv-info','nmea','engine-state','fix-session-state']:
        client.connect(name,on_event,name)
    request=Qmi.MessageLocRegisterEventsInput.new()
    mask=Qmi.LocEventRegistrationFlag.POSITION_REPORT|Qmi.LocEventRegistrationFlag.GNSS_SATELLITE_INFO|Qmi.LocEventRegistrationFlag.NMEA|Qmi.LocEventRegistrationFlag.ENGINE_STATE|Qmi.LocEventRegistrationFlag.FIX_SESSION_STATE
    request.set_event_registration_mask(mask)
    client.register_events(request,10,None,registered,None)
@cb
def opened(source,result,*args):
    source.open_finish(result)
    device.allocate_client(Qmi.Service.LOC,Qmi.CID_NONE,10,None,allocated,None)
@cb
def device_ready(source,result,*args):
    global device
    device=Qmi.Device.new_from_node_finish(result)
    device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS,10,None,opened,None)
@cb
def bus_ready(source,result,*args):
    global bus
    bus=Qrtr.Bus.new_finish(result)
    node=bus.get_node(0)
    assert node is not None
    Qmi.Device.new_from_node(node,None,device_ready,None)
GLib.timeout_add_seconds(110,stop)
GLib.timeout_add_seconds(125,hard_end)
Qrtr.Bus.new(2000,None,bus_ready,None)
loop.run()
write_state()
print(json.dumps(dict(registered=state['client_registered'],started=state['start_ack'],stopped=state['stop_ack'],events=state['events'],errors=len(state['errors']))))
if state['errors'] or not state['stop_ack']: raise SystemExit(1)
