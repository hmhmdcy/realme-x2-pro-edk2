"""Inspect allocation/copy properties without starting another stream."""
import json
import host
code=r'''
import gi,json
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
result={}
for name in ['videoconvert','identity','camerabin','wrappercamerabinsrc','pipewiresrc']:
 e=Gst.ElementFactory.make(name)
 result[name]=[p.name for p in e.list_properties() if any(w in p.name for w in ['pass','copy','alloc','pool','filter','caps'])]
print(json.dumps(result))
'''
r=host.ssh('python3 -',input=code.encode())
print(r.stdout.decode())
