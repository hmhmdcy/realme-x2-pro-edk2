from pathlib import Path
import json
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
for directory in ['work','']:
 p=SDK/directory
 print(str(p),[x.name for x in p.iterdir() if any(n in x.name for n in ['278','299','package','316'])])
for folder in ['libcamera278-r24-r3-built','libcamera299-inline']:
 tree=SDK/'work'/folder
 print(folder,'exists',tree.exists())
 options=tree/'output/meson-info/intro-buildoptions.json'
 if options.exists():
  d=json.loads(options.read_text());print({x['name']:x['value'] for x in d if x['name'] in ['pipelines','ipas','gstreamer','cam','qcam','v4l2','pycamera','test','buildtype','werror','prefix','libdir','sysconfdir','ipa-priv-key']})
 for rel in ['src/libcamera/pipeline/meson.build','src/ipa/meson.build','include/libcamera/ipa/meson.build']:
  p=tree/rel
  if folder=='libcamera299-inline':print(rel,p.read_text()[:5000])
camss=Path('/home/cy122/x2pro-linux/camera314-streams-kernel/drivers/media/platform/qcom/camss')
for name in ['camss-vfe-175.c','camss-vfe.c']:
 p=camss/name
 if p.exists():
  lines=p.read_text().splitlines();hits=[i for i,s in enumerate(lines) if any(word in s for word in ['set_selection','set_compose','compose.width','scale_cfg','scaler_config'])]
  for i in hits[:15]:print(name,i+1,'\n'.join(lines[max(0,i-3):i+12]))
