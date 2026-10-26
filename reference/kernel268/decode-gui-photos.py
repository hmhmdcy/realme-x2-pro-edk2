"""Decode only JPEGs created by our recorded GUI runs; never display scene data."""
from pathlib import Path
import host,json
code=r'''
from pathlib import Path
import hashlib,json,gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None);results=[]
for run in ['r3','r5']:
 d=json.loads(Path('/var/lib/samurai/k268-snapshot-gui-'+run+'/gui-control-summary-private.json').read_text())
 for photo in d['new_jpegs']:
  f=Path(photo['path']);data=f.read_bytes();assert hashlib.sha256(data).hexdigest()==photo['sha256'] and len(data)==photo['bytes']
  pipeline=Gst.Pipeline.new(None)
  src=Gst.ElementFactory.make('filesrc');src.set_property('location',str(f))
  dec=Gst.ElementFactory.make('jpegdec');conv=Gst.ElementFactory.make('videoconvert');sink=Gst.ElementFactory.make('appsink')
  sink.set_property('caps',Gst.Caps.from_string('video/x-raw,format=RGB'));sink.set_property('sync',False);sink.set_property('max-buffers',1)
  for e in [src,dec,conv,sink]:assert e;pipeline.add(e)
  assert src.link(dec) and dec.link(conv) and conv.link(sink)
  try:
   assert pipeline.set_state(Gst.State.PLAYING)!=Gst.StateChangeReturn.FAILURE
   sample=sink.emit('try-pull-sample',8*Gst.SECOND);assert sample,'JPEG did not decode'
   caps=sample.get_caps().get_structure(0);buf=sample.get_buffer();ok,m=buf.map(Gst.MapFlags.READ);assert ok
   try:
    b=bytes(m.data);stride=len(b)//caps.get_value('height');w=caps.get_value('width');h=caps.get_value('height')
    rgb=b''.join(b[y*stride:y*stride+w*3] for y in range(h));assert len(rgb)==w*h*3
    results.append(dict(run=run,camera=photo['camera'],jpeg_bytes=len(data),sha256=photo['sha256'],decoded=True,width=w,height=h,
     rgb_min=min(rgb),rgb_max=max(rgb),mean_channels=[round(sum(rgb[c::3])/(w*h),3) for c in range(3)]))
   finally:buf.unmap(m)
  finally:pipeline.set_state(Gst.State.NULL)
print(json.dumps(dict(stage=268,photos=results,scene_pixels_not_exported=True)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=50)
d=json.loads(q.stdout);(Path(__file__).parent/'gui-jpeg-decode-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
