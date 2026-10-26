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
which=sys.argv[1];run=int(sys.argv[2]);assert which in ['front','rear'] and run in range(1,19)
target='Built-in Front Camera' if which=='front' else 'imx319'
wanted='ac4b000' if which=='front' else 'ac4a000'
devices=[d for d in provider.get_devices() if wanted in str(d.get_properties().get_value('node.name'))];assert len(devices)==1
props=devices[0].get_properties();wanted='ac4b000' if which=='front' else 'ac4a000'
assert wanted in props.get_value('node.name') and props.get_value('node.reliable')=='true'
pipeline=Gst.Pipeline.new(None);source=devices[0].create_element('camera')
expected_plugin=('/var/lib/samurai/k265-candidate-v4/libgstpipewire.so' if run>=12 else ('/var/lib/samurai/k265-candidate-v3/libgstpipewire.so' if run>=10 else '/var/lib/samurai/k265-candidate/libgstpipewire.so')) if os.environ.get('K265_CANDIDATE_PLUGIN')=='1' else '/usr/lib/gstreamer-1.0/libgstpipewire.so'
assert source.get_factory().get_plugin().get_filename()==expected_plugin
assert source.get_property('use-bufferpool') is True and os.environ.get('SAMURAI_CAMERA_COPY') is None
scenario=6000000 if run==2 else 2000001
default_policy_verified=False
if scenario==4000000:
 assert source.get_factory().get_plugin().get_filename()=='/usr/lib/gstreamer-1.0/libgstpipewire.so'
 assert source.get_property('use-bufferpool') is False
 previous=os.environ.pop('SAMURAI_CAMERA_COPY')
 control=devices[0].create_element('default-policy-control')
 assert control.get_property('use-bufferpool') is True
 assert devices[0].reconfigure_element(source)
 assert source.get_property('use-bufferpool') is False
 os.environ['SAMURAI_CAMERA_COPY']=previous
 default_policy_verified=True
if scenario in [3000000,3000001,3000002]:
 assert source.get_factory().get_plugin().get_filename()==('/usr/lib/gstreamer-1.0/libgstpipewire.so' if os.environ.get('K264_SYSTEM_PLUGIN')=='1' else '/var/lib/samurai/k264-candidate/libgstpipewire.so')
 if scenario==3000000:source.set_property('use-bufferpool',False)
 assert source.get_property('use-bufferpool') is False
width,height=(1920,1080) if which=='front' else (1600,1200)
caps=Gst.ElementFactory.make('capsfilter');caps.props.caps=Gst.Caps.from_string(f'video/x-raw,format=BGRx,width={width},height={height}')
delay=Gst.ElementFactory.make('identity');delay.set_property('sleep-time',scenario if scenario<1000000 else 0)
sink=Gst.ElementFactory.make('fakesink');sink.props.sync=False;sink.props.signal_handoffs=True;sink.props.enable_last_sample=False
data=dict(buffers=0,pts=[],caps=None,errors=[],eos=False,shared_bufferpool=source.get_property('use-bufferpool') if source.find_property('use-bufferpool') else None,source_factory=source.get_factory().get_name(),upstream_default_and_reconfigure_verified=default_policy_verified)
data['source_plugin']=source.get_factory().get_plugin().get_filename()
data['application_copy_env']=os.environ.get('SAMURAI_CAMERA_COPY')
props=devices[0].get_properties();data['remote_node_reliable']=str(props.get_value('node.reliable')) if props.has_field('node.reliable') else None
held=[];samples=[]
stress=run in range(6,19)
hold_seconds=.35 if stress else .12
duration=24.0 if stress else 14.0
data.update(held_checked=0,held_content_changed=0,held_bytes_sampled=65536,held_pts_changed=0,held_change_details=[])
def handoff(sink,buffer,pad):
 data['buffers']+=1
 data['pts'].append(buffer.pts)
 if run!=3 and data['buffers']%15==0:
  current=pad.get_current_caps().get_structure(0);w=current.get_value('width');h=current.get_value('height');size=buffer.get_size();stride=size//h
  assert size%h==0 and stride>=w*4
  pixels=buffer.extract_dup(0,size);values=[]
  for y in range(0,h,max(1,h//48)):
   for x in range(0,w,max(1,w//64)):
    offset=y*stride+x*4;values.append((int(pixels[offset])+int(pixels[offset+1])+int(pixels[offset+2]))/3)
  samples.append(dict(frame=data['buffers'],pts=int(buffer.pts),mean=sum(values)/len(values),min=min(values),max=max(values),dark_fraction=sum(v<8 for v in values)/len(values),bright_fraction=sum(v>247 for v in values)/len(values)))

 if data['caps'] is None:data['caps']=pad.get_current_caps().to_string()
 if hold_seconds>0:held.append((time.monotonic(),buffer.copy(),hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest(),buffer.get_size(),buffer.pts,buffer.n_memory(),buffer.offset))
sink.connect('handoff',handoff)
capture=scenario in [2000000,2000001,3000002]
if capture:
 wrapper=Gst.ElementFactory.make('wrappercamerabinsrc');wrapper.set_property('video-source',source)
 pipeline=Gst.ElementFactory.make('camerabin')
 pipeline.set_property('camera-source',wrapper)
 pipeline.set_property('viewfinder-sink',sink)
 pipeline.set_property('viewfinder-caps',caps.props.caps)
 pipeline.set_property('image-capture-caps',caps.props.caps)
 private_root=Path('/var/lib/samurai/k267-user')/('camera-'+str(run));assert not private_root.exists();private_root.mkdir(mode=0o700)
 photo=private_root/'photo-private.jpg'
 assert not photo.exists()
 pipeline.set_property('location',str(photo));pipeline.set_property('mode',1)
else:
 for e in [source,caps,delay,sink]:pipeline.add(e)
 assert source.link(caps) and caps.link(delay) and delay.link(sink)
bus=pipeline.get_bus();start=time.monotonic()
triggered=False;photo_done=False;shots=[];shot_active=False;last_shutter_frame=0
try:
 assert pipeline.set_state(Gst.State.PLAYING)!=Gst.StateChangeReturn.FAILURE
 while time.monotonic()-start<duration:
  while held and time.monotonic()-held[0][0]>hold_seconds:
   timestamp,buffer,digest,original_size,original_pts,original_memories,original_offset=held.pop(0)
   data['held_checked']+=1
   changed=hashlib.sha256(buffer.extract_dup(0,min(65536,buffer.get_size()))).digest()!=digest
   pts_changed=buffer.pts!=original_pts
   data['held_content_changed']+=changed;data['held_pts_changed']+=pts_changed
   if changed or pts_changed:
    data['held_change_details'].append(dict(elapsed_ms=(time.monotonic()-start)*1000,before_size=original_size,after_size=buffer.get_size(),before_pts=original_pts,after_pts=buffer.pts,before_memories=original_memories,after_memories=buffer.n_memory(),before_offset=original_offset,after_offset=buffer.offset))
   del buffer
  should_shoot=capture and ((not stress and not triggered and data['buffers']>50) or (stress and len(shots)<3 and not shot_active and data['buffers']>50+len(shots)*140))
  if should_shoot:
   if stress:
    photo=private_root/('shot-'+str(len(shots))+'-private.jpg');assert not photo.exists();pipeline.set_property('location',str(photo))
   pipeline.emit('start-capture');triggered=True;shot_active=True;last_shutter_frame=data['buffers']
  m=bus.timed_pop_filtered(100*Gst.MSECOND,Gst.MessageType.ERROR|Gst.MessageType.EOS|Gst.MessageType.ELEMENT)
  if m:
   if m.type==Gst.MessageType.ERROR:
    e,debug=m.parse_error();data['errors'].append(dict(message=str(e),debug=debug));break
   if m.type==Gst.MessageType.EOS:data['eos']=True;break
   structure=m.get_structure()
   if structure and structure.get_name()=='image-done':
    photo_done=True;shot_active=False
    shots.append(dict(index=len(shots),preview_frame=last_shutter_frame,bytes=photo.stat().st_size,sha256=hashlib.sha256(photo.read_bytes()).hexdigest()))
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
data['scenario_code']=scenario
data['consumer_delay_us']=scenario if scenario<1000000 else 0
data['retain_frames_for_ms']=hold_seconds*1000
if capture:
 data['shutter_triggered']=triggered;data['image_done_message']=photo_done
 data['saved_jpeg_bytes']=photo.stat().st_size if photo.exists() else 0
 data['jpeg_sha256']=hashlib.sha256(photo.read_bytes()).hexdigest() if photo.exists() else None
data.update(camera_selected=which,target_display_name=target,sampled_preview_frames=samples,shots=shots)
print(json.dumps(data),flush=True)
assert data['buffers']>20 and not data['errors'] and data['stopped']
if capture:assert photo_done and photo.exists() and photo.stat().st_size>1024

assert data['held_checked']>20 and data['held_content_changed']==0 and data['held_pts_changed']==0 and data['pts_strictly_increasing'] and data['application_copy_env'] is None

if stress:assert len(shots)==3 and all(x['bytes']>1024 for x in shots)
