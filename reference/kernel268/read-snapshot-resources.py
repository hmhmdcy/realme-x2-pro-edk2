"""Inspect installed UI definitions without changing the camera application."""
import json
import xml.etree.ElementTree as ET
import host

code=r'''
from pathlib import Path
import gi,json
gi.require_version('Gio','2.0')
from gi.repository import Gio,GLib
results={};files=[p for p in Path('/usr/share/snapshot').rglob('*') if p.is_file()]
for p in files:
 if p.suffix=='.ui':results[str(p)]=p.read_text()
binary=Path('/usr/bin/snapshot').read_bytes();offsets=[];pos=0
while True:
 pos=binary.find(b'GVariant',pos)
 if pos<0:break
 offsets.append(pos);pos+=8
assert len(offsets)<30
resources=[Gio.Resource.load(str(p)) for p in files if p.suffix=='.gresource']
for off in offsets:
 try:resources.append(Gio.Resource.new_from_data(GLib.Bytes.new(binary[off:])))
 except GLib.Error:pass
for res in resources:
 pending=['/'];seen=set()
 while pending and len(seen)<400:
  path=pending.pop()
  if path in seen:continue
  seen.add(path)
  try:children=res.enumerate_children(path,Gio.ResourceLookupFlags.NONE)
  except GLib.Error:continue
  for child in children:
   name=path+child
   if child.endswith('/'):pending.append(name)
   elif name.endswith(('.ui','.blp')):
    data=res.lookup_data(name,Gio.ResourceLookupFlags.NONE).get_data().decode()
    if any(x in name.lower() for x in ['window','camera','preferences']):results[name]=data
print(json.dumps(dict(installed_files=[str(p) for p in files],resource_candidates=len(offsets),ui=results)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'snapshot-ui-source-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);print(json.dumps(dict(resource_candidates=d['resource_candidates'],ui_paths=list(d['ui']))))
for name,text in d['ui'].items():
 print(name)
 root=ET.fromstring(text)
 for obj in root.iter('object'):
  attrs=obj.attrib;props={p.get('name'):p.text for p in obj.findall('property')}
  if any(x in str(attrs).lower()+str(props).lower() for x in ['camera','switch','device','preferences']):
   print(json.dumps(dict(attributes=attrs,properties=props)))
