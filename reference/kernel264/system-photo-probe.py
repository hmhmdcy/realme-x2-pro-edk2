"""Exercise one real PipeWire camera with a bounded, optionally slow consumer."""
import hashlib,json,os,sys,time
from pathlib import Path
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst,GLib
Gst.init(None)
provider=Gst.DeviceProviderFactory.find('pipewiredeviceprovider').get()
assert provider.start()
ctx=GLib.MainContext.default();deadline=time.monotonic()+4
while time.monotonic()<deadline:
 while ctx.pending():ctx.iteration(False)
 time.sleep(.02)
devices=[d for d in provider.get_devices() if d.get_display_name()=='Built-in Front Camera']
assert len(devices)==1
pipeline=Gst.Pipeline.new(None)
source=devices[0].create_element('camera') if int(sys.argv[1])!=6000007 else Gst.ElementFactory.make('libcamerasrc')
if int(sys.argv[1])==6000007:source.set_property('camera-name','/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10')
if int(sys.argv[1])==6000000:
 assert source.get_factory().get_plugin().get_filename()==('/usr/lib/gstreamer-1.0/libgstpipewire.so' if os.environ.get('K264_SYSTEM_PLUGIN')=='1' else '/var/lib/samurai/k264-candidate/libgstpipewire.so')
 assert source.get_property('use-bufferpool') is True
default_policy_verified=False
if int(sys.argv[1])==4000000:
 assert source.get_factory().get_plugin().get_filename()=='/usr/lib/gstreamer-1.0/libgstpipewire.so'
 assert source.get_property('use-bufferpool') is False
 previous=os.environ.pop('SAMURAI_CAMERA_COPY')
 control=devices[0].create_element('default-policy-control')
 assert control.get_property('use-bufferpool') is True
 assert devices[0].reconfigure_element(source)
 assert source.get_property('use-bufferpool') is False
 os.environ['SAMURAI_CAMERA_COPY']=previous
 default_policy_verified=True
if int(sys.argv[1]) in [3000000,3000001,3000002]:
 assert source.get_factory().get_plugin().get_filename()==('/usr/lib/gstreamer-1.0/libgstpipewire.so' if os.environ.get('K264_SYSTEM_PLUGIN')=='1' else '/var/lib/samurai/k264-candidate/libgstpipewire.so')
 if int(sys.argv[1])==3000000:source.set_property('use-bufferpool',False)
 assert source.get_property('use-bufferpool') is False
caps=Gst.ElementFactory.make('capsfilter');caps.props.caps=Gst.Caps.from_string('video/x-raw,width=1920,height=1080,format=BGRx')
delay=Gst.ElementFactory.make('identity');delay.set_property('sleep-time',int(sys.argv[1]) if int(sys.argv[1])<1000000 else 0)
sink=Gst.ElementFactory.make('fakesink');sink.props.sync=False;sink.props.signal_handoffs=True;sink.props.enable_last_sample=False
data=dict(buffers=0,pts=[],caps=None,errors=[],eos=False,shared_bufferpool=source.get_property('use-bufferpool') if source.find_property('use-bufferpool') else None,source_factory=source.get_factory().get_name(),upstream_default_and_reconfigure_verified=default_policy_verified)
data['source_plugin']=source.get_factory().get_plugin().get_filename()
data['application_copy_env']=os.environ.get('SAMURAI_CAMERA_COPY')
props=devices[0].get_properties();data['remote_node_reliable']=str(props.get_value('node.reliable')) if props.has_field('node.reliable') else None
held=[]
hold_seconds=float(os.environ.get('K264_HOLD_SECONDS','.12'))
duration=float(os.environ.get('K264_DURATION','12'))
data.update(held_checked=0,held_content_changed=0,held_bytes_sampled=65536,held_pts_changed=0,held_change_details=[])
def handoff(sink,buffer,pad):
 data['buffers']+=1
 data['pts'].append(buffer.pts)
 if data['caps'] is None:data['caps']=pad.get_current_caps().to_string()
 if hold_seconds>0:held.append((time.monotonic(),buffer.copy(),hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest(),buffer.get_size(),buffer.pts,buffer.n_memory()))
sink.connect('handoff',handoff)
capture=int(sys.argv[1]) in [2000000,2000001,3000002]
if capture:
 wrapper=Gst.ElementFactory.make('wrappercamerabinsrc');wrapper.set_property('video-source',source)
 pipeline=Gst.ElementFactory.make('camerabin')
 pipeline.set_property('camera-source',wrapper)
 pipeline.set_property('viewfinder-sink',sink)
 pipeline.set_property('viewfinder-caps',caps.props.caps)
 pipeline.set_property('image-capture-caps',caps.props.caps)
 photo=Path(os.environ['K264_PHOTO_PATH'])
 assert not photo.exists()
 pipeline.set_property('location',str(photo));pipeline.set_property('mode',1)
else:
 for e in [source,caps,delay,sink]:pipeline.add(e)
 assert source.link(caps) and caps.link(delay) and delay.link(sink)
bus=pipeline.get_bus();start=time.monotonic()
triggered=False;photo_done=False
try:
 assert pipeline.set_state(Gst.State.PLAYING)!=Gst.StateChangeReturn.FAILURE
 while time.monotonic()-start<duration:
  while held and time.monotonic()-held[0][0]>hold_seconds:
   timestamp,buffer,digest,original_size,original_pts,original_memories=held.pop(0)
   data['held_checked']+=1
   changed=hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest()!=digest
   pts_changed=buffer.pts!=original_pts
   data['held_content_changed']+=changed;data['held_pts_changed']+=pts_changed
   if changed or pts_changed:
    data['held_change_details'].append(dict(elapsed_ms=(time.monotonic()-start)*1000,before_size=original_size,after_size=buffer.get_size(),before_pts=original_pts,after_pts=buffer.pts,before_memories=original_memories,after_memories=buffer.n_memory()))
   del buffer
  if capture and not triggered and data['buffers']>50:
   pipeline.emit('start-capture');triggered=True
  m=bus.timed_pop_filtered(100*Gst.MSECOND,Gst.MessageType.ERROR|Gst.MessageType.EOS|Gst.MessageType.ELEMENT)
  if m:
   if m.type==Gst.MessageType.ERROR:
    e,debug=m.parse_error();data['errors'].append(dict(message=str(e),debug=debug));break
   if m.type==Gst.MessageType.EOS:data['eos']=True;break
   structure=m.get_structure()
   if structure and structure.get_name()=='image-done':photo_done=True
finally:
 held.clear()
 pipeline.set_state(Gst.State.NULL)
 state=pipeline.get_state(5*Gst.SECOND)
 data['stopped']=state.state==Gst.State.NULL
 provider.stop()
data['elapsed']=time.monotonic()-start
pts=data.pop('pts');data['pts_count']=len(pts)
data['pts_strictly_increasing']=len(pts)>1 and all(b>a for a,b in zip(pts,pts[1:]))
data['pts_span_seconds']=(pts[-1]-pts[0])/Gst.SECOND if len(pts)>1 else 0
data['pts_max_gap_seconds']=max((b-a)/Gst.SECOND for a,b in zip(pts,pts[1:])) if len(pts)>1 else 0
data['pts_regressions']=[dict(index=i+1,before=a,after=b) for i,(a,b) in enumerate(zip(pts,pts[1:])) if b<=a]
data['scenario_code']=int(sys.argv[1])
data['consumer_delay_us']=int(sys.argv[1]) if int(sys.argv[1])<1000000 else 0
data['retain_frames_for_ms']=hold_seconds*1000
if capture:
 data['shutter_triggered']=triggered;data['image_done_message']=photo_done
 data['saved_jpeg_bytes']=photo.stat().st_size if photo.exists() else 0
 data['jpeg_sha256']=hashlib.sha256(photo.read_bytes()).hexdigest() if photo.exists() else None
print(json.dumps(data),flush=True)
assert data['buffers']>20 and not data['errors'] and data['stopped']
if capture:assert photo_done and photo.exists() and photo.stat().st_size>1024
