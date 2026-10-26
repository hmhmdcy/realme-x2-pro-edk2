"""Independent reader for the retained aligned v1.1 mode and module tables."""
from pathlib import Path
import struct

class ModeTree:
 def __init__(self,path):
  raw=Path(path).read_bytes();self.path=Path(path)
  version=struct.unpack_from('<Q',raw,32)[0];assert version==0x10001,hex(version)
  table,count=struct.unpack_from('<II',raw,0x98)
  sections={kind:(start,length) for kind,start,length in [struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]}
  start,length=sections[2];assert length%24==0;self.nodes={}
  for pos in range(start,start+length,24):
   uid,value,parent=struct.unpack_from('<QQQ',raw,pos)
   self.nodes[uid]=dict(id=uid,type=value&65535,sub=(value>>16)&65535,group=value>>32,parent=parent,children=[],groups=[],modules=[])
  for uid,node in self.nodes.items():
   if uid==0:continue
   parent=self.nodes[node['parent']];same=(node['type'],node['sub'])==(parent['type'],parent['sub'])
   parent['groups' if same else 'children'].append(uid)
  start,length=sections[0];assert length%72==0;self.modules={}
  for pos in range(start,start+length,72):
   uid=struct.unpack_from('<Q',raw,pos)[0];modeid=struct.unpack_from('<Q',raw,pos+48)[0]
   if modeid==0xffffffff:continue
   name=raw[pos+8:pos+40].split(b'\0')[0].decode();assert modeid in self.nodes
   row=dict(uid=uid,name=name,mode_id=modeid,path=self.route(modeid));self.modules[uid]=row;self.nodes[modeid]['modules'].append(row)
 def route(self,uid):
  result=[]
  while uid:
   node=self.nodes[uid];parent=self.nodes[node['parent']]
   if (node['type'],node['sub'])!=(parent['type'],parent['sub']):result.append([node['type'],node['sub']])
   uid=node['parent']
  return [[0,0]]+result[::-1]
 def local(self,node,tag):
  for row in node['modules']:
   if row['name']==tag:return row
  for uid in node['groups']:
   result=self.local(self.nodes[uid],tag)
   if result:return result
  return None
 def select(self,tag,values):
  node=self.nodes[0];result=self.local(node,tag)
  for kind,sub in enumerate(values[1:],1):
   child=next((self.nodes[uid] for uid in node['children'] if (self.nodes[uid]['type'],self.nodes[uid]['sub'])==(kind,sub)),None)
   if child is None:break
   node=child;result=self.local(node,tag) or result
  return result

