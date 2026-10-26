from pathlib import Path
import ctypes,importlib.util,math,struct,sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ccm_oracle340',HERE.parent/'kernel340/oracle.py');ccm=importlib.util.module_from_spec(spec);spec.loader.exec_module(ccm)
CHANNELS=['r','gr','gb','b'];Mesh=ctypes.c_float*884
class LscOracle:
 def __init__(self,private):
  self.ccm=ccm.Oracle(private);self.lib=ctypes.CDLL(str(Path(private)/'pinned-lsc-oracle-private.so'));self.lib.blend.argtypes=[ctypes.POINTER(Mesh),ctypes.POINTER(Mesh),ctypes.c_float,ctypes.POINTER(Mesh)];self.lib.calibrate.argtypes=[ctypes.POINTER(Mesh)]*4
  text=(HERE.parent/'kernel319/check-factory-resampling.py').read_text();ns={'math':math,'struct':struct};exec(text[text.index('def geometry'):text.index('\ncases=')],ns);self.geometry=ns['geometry'];self.predict=ns['predict'];self.cache={}
 def pack(self,source,profile,size):
  mapping=[*profile['source_span'],*profile['first_quad'],*profile['quad_step']];key=(bytes(source),tuple(mapping),tuple(size))
  if key in self.cache:return self.cache[key]
  grid=self.geometry(*size);codes=[]
  for i in range(4):codes.extend(math.floor(v*1024+.5) for v in self.predict(source[i*221:(i+1)*221],grid,mapping))
  packet=struct.pack('<HHI4HB7x884H',6,2,1792,*grid,*codes);assert len(packet)==1792;self.cache[key]=packet;return packet
 def evaluate(self,profile,kelvin,aec,size):
  reference=profile['reference_triggers'];hdr={'exposure_time_ratio':0,'sensitivity_ratio':2,'exposure_gain_ratio':4}[profile['hdr_control']];aecpos=0 if profile['aec_control']=='lux_index' else 2
  def visit(nodes,level):
   def child(node):return Mesh(*[v for c in CHANNELS for v in node['gains'][c]]) if level==5 else visit(node['children'],level+1)
   if level==3:return child(next(node for node in nodes if node['trigger'][0]==reference['led_index']))
   position=hdr if level==2 else aecpos if level==4 else 0;value=kelvin if level==5 else aec if level==4 else reference[{0:'lens_position',1:'drc_gain',2:'hdr_ratio'}[level]]
   regions=(ccm.Region*len(nodes))(*(ccm.Region(*node['trigger'][position:position+2]) for node in nodes));selected=ccm.Selection();self.ccm.lib.choose(regions,len(nodes),value,ctypes.byref(selected));a=child(nodes[selected.first])
   if selected.first==selected.second:return a
   b=child(nodes[selected.second]);output=Mesh();self.lib.blend(ctypes.byref(a),ctypes.byref(b),selected.weight,ctypes.byref(output));return output
  source=visit(profile['core'],0)
  if 'golden' in profile:
   golden=Mesh(*[v for c in CHANNELS for v in profile['golden'][c]]);unit=Mesh(*[v for c in CHANNELS for v in profile['unit'][c]]);result=Mesh();self.lib.calibrate(ctypes.byref(source),ctypes.byref(golden),ctypes.byref(unit),ctypes.byref(result));source=result
  return self.pack(source,profile,size)
 def unity(self,profile,size):return self.pack(Mesh(*([1.]*884)),profile,size)
def trace(packet):
 value=2166136261
 for byte in packet:value=((value^byte)*16777619)&0xffffffff
 return value
