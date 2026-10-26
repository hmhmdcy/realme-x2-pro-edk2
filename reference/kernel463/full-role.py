"""Resolve CAMSS FULL from PIX links, then check a caller-owned runtime witness.

Import is inert. This module neither connects to a device nor writes tracefs.
"""
from pathlib import PurePosixPath
import hashlib,json,re

class RoleError(ValueError):pass
def require(value,message):
 if not value:raise RoleError(message)
def sha(data):return hashlib.sha256(data).hexdigest()

def camss_graph(text):
 require(isinstance(text,str) and len(text.encode())<=2*1024*1024,'bounded media graph required')
 documents=re.split(r'(?=^Media controller API version )',text,flags=re.M)
 matches=[d for d in documents if re.search(r'^driver\s+qcom-camss\s*$',d,re.M)]
 require(len(matches)==1,'exactly one qcom-camss graph required')
 document=matches[0]
 require(re.search(r'^bus info\s+platform:acb3000\.camss\s*$',document,re.M),'wrong CAMSS platform')
 entities={};current=None;pad=None
 for line in document.splitlines():
  match=re.fullmatch(r'- entity (\d+): (.+) \(\d+ pads?, \d+ links?(?:, \d+ routes?)?\)',line)
  if match:
   name=match[2];require(name not in entities,'duplicate media entity')
   current={'id':int(match[1]),'name':name,'pads':{},'node':None,'kind':None};entities[name]=current;pad=None;continue
  if current is None:continue
  match=re.match(r'\s+type (Node|V4L2 subdev) ',line)
  if match:current['kind']=match[1];continue
  match=re.fullmatch(r'\s+device node name (\S+)',line)
  if match:
   require(current['node'] is None,'duplicate device node');current['node']=match[1];continue
  match=re.fullmatch(r'\s+pad(\d+): (SOURCE|SINK)',line)
  if match:
   pad=int(match[1]);require(pad not in current['pads'],'duplicate pad')
   current['pads'][pad]={'kind':match[2],'links':[]};continue
  match=re.fullmatch(r'\s+(->|<-) "([^"]+)":(\d+) \[([^\]]*)\]',line)
  if match:
   require(pad is not None,'link without pad')
   current['pads'][pad]['links'].append(dict(direction=match[1],entity=match[2],pad=int(match[3]),flags=set(match[4].split(','))))
 return entities

def discover(probe_bytes,graph_bytes,pixel_entity):
 require(re.fullmatch(r'msm_vfe\d+_pix',pixel_entity),'FULL must originate at a PIX entity')
 probe=json.loads(probe_bytes);entities=camss_graph(graph_bytes.decode())
 require(pixel_entity in entities,'PIX missing from graph')
 pix=entities[pixel_entity]
 require(pix['kind']=='V4L2 subdev' and 1 in pix['pads'] and pix['pads'][1]['kind']=='SOURCE','PIX full source pad missing')
 links=[link for link in pix['pads'][1]['links'] if link['direction']=='->']
 require(len(links)==1,'ambiguous PIX full source')
 link=links[0];require(link['flags']=={'ENABLED','IMMUTABLE'},'FULL link is not enabled immutable')
 require(link['entity'] in entities,'FULL remote entity missing')
 full=entities[link['entity']]
 require(full['kind']=='Node' and full['node'] is not None,'FULL is not a video node')
 require(set(full['pads'])=={link['pad']} and full['pads'][link['pad']]['kind']=='SINK','FULL sink pad mismatch')
 back=full['pads'][link['pad']]['links']
 require(len(back)==1 and back[0]==dict(direction='<-',entity=pixel_entity,pad=1,flags={'ENABLED','IMMUTABLE'}),'FULL backlink mismatch')
 require(re.fullmatch(r'/dev/video\d+',full['node']),'unsafe FULL device path')
 node=PurePosixPath(full['node']).name
 require(node in probe['video_nodes'],'FULL missing from actual video inventory')
 item=probe['video_nodes'][node]
 require(item['name']==full['name'] and re.fullmatch(r'\d+:\d+',item['dev']),'FULL inventory/entity mismatch')
 major,minor=map(int,item['dev'].split(':'))
 return dict(schema='samurai-camss-full-role-v1',pixel_entity=pixel_entity,pixel_source_pad=1,
             full_entity=full['name'],full_video_node=node,full_device=full['node'],major=major,minor=minor,
             probe_sha256=sha(probe_bytes),graph_sha256=sha(graph_bytes),
             topology_role_verified=True,runtime_open_fd_verified=False,actual_v4l2_emission_verified=False)

def check_selection(role,selection):
 require(role.get('schema')=='samurai-camss-full-role-v1' and role.get('topology_role_verified') is True,'role proof missing')
 require(selection['full_video_node']==role['full_video_node'] and selection['full_minor']==role['minor'],
         'trace filter is not the PIX/FULL device proven by topology')
 require(selection['probe_sha256']==role['probe_sha256'],'selection uses another inventory')

def check_open_fd(role,witness,expected):
 """Validate one collected witness; this function does not make it fresh/live."""
 require(witness['same_process_before_after'] is True,'process changed during query')
 for key in ['pid','start_ticks','exe_sha256','uid','cap_eff']:
  require(witness['identity'][key]==expected[key],'application identity mismatch: '+key)
 require(expected['uid']==10000 and expected['cap_eff']==0,'unprivileged application required')
 matches=[fd for fd in witness['character_fds'] if fd['major']==role['major'] and fd['minor']==role['minor']]
 require(matches and all(fd['target']==role['full_device'] for fd in matches),'application has no matching FULL device FD')
 return dict(open_fd_count=len(matches),actual_process_fd_verified=True)

def check_emission(role,events):
 """An available/enabled tracepoint is insufficient: require observed ioctls."""
 q=[e for e in events if e.get('event')=='v4l2_qbuf' and e.get('minor')==role['minor']]
 dq=[e for e in events if e.get('event')=='v4l2_dqbuf' and e.get('minor')==role['minor']]
 require(q and dq,'no observed FULL v4l2 qbuf/dqbuf pair; do not accept emission')
 return dict(qbuf_events=len(q),dqbuf_events=len(dq),actual_v4l2_emission_verified=True)

def from_observation(probe_bytes,observation_bytes,pixel_entity,expected_boot,expected_window,expected_identity):
 """Consume a trusted transport result; it is not an owner/SSH authorization."""
 observation=json.loads(observation_bytes);probe=json.loads(probe_bytes)
 require(observation.get('schema')=='samurai-full-role-observation-v1' and observation.get('phone_changed') is False,'not a read-only role observation')
 require(observation['boot_id']==expected_boot and observation['window_id']==expected_window,'role observation belongs to another boot/window')
 require(observation['video_nodes']==probe['video_nodes'],'role observation inventory differs from trace capability probe')
 require(0<observation['mono_start_ns']<=observation['mono_end_ns'],'invalid observation times')
 result=discover(probe_bytes,observation['graph']['text'].encode(),pixel_entity)
 check_open_fd(result,observation,expected_identity)
 result.update(runtime_open_fd_verified=True,observation_sha256=sha(observation_bytes))
 return result
