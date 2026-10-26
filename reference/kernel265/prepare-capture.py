"""Reuse the bounded production harness while keeping normal libcamera graph ownership."""
from pathlib import Path
R=Path(__file__).parent;old=R.parent/'kernel264'
s=(old/'native-system-natural.py').read_text()
s=s.replace("which,kind='front','rgb';delay=int(sys.argv[1]);assert delay in range(6000080,6000085)","which,kind=sys.argv[1],'rgb';delay=int(sys.argv[2]);assert which in ['front','rear'] and delay in range(1,10)")
s=s.replace("out=root/('k264-pipewire-'+str(delay)+'-r2')","out=root/('k265-camera-'+str(delay))")
s=s.replace('stage=264','stage=265').replace("instances/k264_pipewire","instances/k265_camera")
s=s.replace("args=['/usr/bin/python3','/var/lib/samurai/k264-tools/system-runner.py',str(delay)]","args=['/usr/bin/python3','/var/lib/samurai/k265-tools/camera-probe.py',which,str(delay)]")
s=s.replace("application='camerabin-system-photo' if delay==6000084 else 'camera-clients'","application='camerabin-standard-photo',camera_selected=which")
s=s.replace('no_shutter_action=delay!=6000084,no_scene_images_saved=delay!=6000084','no_shutter_action=False,no_scene_images_saved=False')
(R/'native-capture.py').write_text(s)
s=(old/'system-photo-probe.py').read_text()
start=s.index("devices=[d for d in provider.get_devices()")
end=s.index('default_policy_verified=False',start)
s=s[:start]+'''which=sys.argv[1];run=int(sys.argv[2]);assert which in ['front','rear'] and run in range(1,10)
target='Built-in Front Camera' if which=='front' else 'imx319'
devices=[d for d in provider.get_devices() if d.get_display_name()==target];assert len(devices)==1
props=devices[0].get_properties();wanted='ac4b000' if which=='front' else 'ac4a000'
assert wanted in props.get_value('node.name') and props.get_value('node.reliable')=='true'
pipeline=Gst.Pipeline.new(None);source=devices[0].create_element('camera')
assert source.get_factory().get_plugin().get_filename()=='/usr/lib/gstreamer-1.0/libgstpipewire.so'
assert source.get_property('use-bufferpool') is True and os.environ.get('SAMURAI_CAMERA_COPY') is None
scenario=2000001
''' + s[end:]
s=s.replace('int(sys.argv[1])','scenario')
s=s.replace("video/x-raw,width=1920,height=1080,format=BGRx","video/x-raw,format=BGRx,width="+"{width},height={height}")
s=s.replace("caps=Gst.ElementFactory.make('capsfilter');caps.props.caps=Gst.Caps.from_string('video/x-raw,format=BGRx,width={width},height={height}')","width,height=(1920,1080) if which=='front' else (1600,1200)\ncaps=Gst.ElementFactory.make('capsfilter');caps.props.caps=Gst.Caps.from_string(f'video/x-raw,format=BGRx,width={width},height={height}')")
s=s.replace("duration=float(os.environ.get('K264_DURATION','12'))","duration=14.0")
s=s.replace("hold_seconds=float(os.environ.get('K264_HOLD_SECONDS','.12'))","hold_seconds=.12")
s=s.replace("photo=Path(os.environ['K264_PHOTO_PATH'])","private_root=Path('/var/lib/samurai/k265-user')/('camera-'+str(run));assert not private_root.exists();private_root.mkdir(mode=0o700)\n photo=private_root/'photo-private.jpg'")
# Leave the normal camera AE untouched; collect only bounded image samples through public Gst buffers.
needle=" data['pts'].append(buffer.pts)"
assert s.count(needle)==1
s=s.replace(needle,needle+'''
 if data['buffers']%15==0:
  current=pad.get_current_caps().get_structure(0);w=current.get_value('width');h=current.get_value('height');size=buffer.get_size();stride=size//h
  assert size%h==0 and stride>=w*4
  pixels=buffer.extract_dup(0,size);values=[]
  for y in range(0,h,max(1,h//48)):
   for x in range(0,w,max(1,w//64)):
    offset=y*stride+x*4;values.append((int(pixels[offset])+int(pixels[offset+1])+int(pixels[offset+2]))/3)
  samples.append(dict(frame=data['buffers'],pts=int(buffer.pts),mean=sum(values)/len(values),min=min(values),max=max(values),dark_fraction=sum(v<8 for v in values)/len(values),bright_fraction=sum(v>247 for v in values)/len(values)))
''')
s=s.replace("held=[]","held=[];samples=[]",1)
s=s.replace("print(json.dumps(data),flush=True)","data.update(camera_selected=which,target_display_name=target,sampled_preview_frames=samples)\nprint(json.dumps(data),flush=True)")
s += "\nassert data['held_checked']>20 and data['held_content_changed']==0 and data['held_pts_changed']==0 and data['pts_strictly_increasing'] and data['application_copy_env'] is None\n"
(R/'camera-probe.py').write_text(s)
print('Prepared fresh stage265 capture scripts; no phone mutation.')
