"""Exercise repeated standard shutter actions while preview buffers remain retained."""
from pathlib import Path
R=Path(__file__).parent;p=R/'camera-probe.py';s=p.read_text()
s=s.replace('hold_seconds=.12','hold_seconds=.35 if run==6 else .12')
s=s.replace('duration=14.0','duration=24.0 if run==6 else 14.0')
s=s.replace('triggered=False;photo_done=False','triggered=False;photo_done=False;shots=[];shot_active=False;last_shutter_frame=0')
old="""  if capture and not triggered and data['buffers']>50:
   pipeline.emit('start-capture');triggered=True"""
new="""  should_shoot=capture and ((run!=6 and not triggered and data['buffers']>50) or (run==6 and len(shots)<3 and not shot_active and data['buffers']>50+len(shots)*140))
  if should_shoot:
   if run==6:
    photo=private_root/('shot-'+str(len(shots))+'-private.jpg');assert not photo.exists();pipeline.set_property('location',str(photo))
   pipeline.emit('start-capture');triggered=True;shot_active=True;last_shutter_frame=data['buffers']"""
assert s.count(old)==1;s=s.replace(old,new)
old="   if structure and structure.get_name()=='image-done':photo_done=True"
new="""   if structure and structure.get_name()=='image-done':
    photo_done=True;shot_active=False
    shots.append(dict(index=len(shots),preview_frame=last_shutter_frame,bytes=photo.stat().st_size,sha256=hashlib.sha256(photo.read_bytes()).hexdigest()))"""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("data.update(camera_selected=which,target_display_name=target,sampled_preview_frames=samples)","data.update(camera_selected=which,target_display_name=target,sampled_preview_frames=samples,shots=shots)")
s += "\nif run==6:assert len(shots)==3 and all(x['bytes']>1024 for x in shots)\n"
p.write_text(s)
print('Prepared repeated shutter stress; no device action.')
