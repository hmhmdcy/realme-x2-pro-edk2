"""Reuse the pinned CamX selection/interpolation/encoding library from335."""
from pathlib import Path
import ctypes,struct
class Data(ctypes.Structure):_fields_=[('matrix',ctypes.c_float*9),('offsets',ctypes.c_int32*3)]
class Region(ctypes.Structure):_fields_=[('start',ctypes.c_float),('end',ctypes.c_float)]
class Selection(ctypes.Structure):_fields_=[('first',ctypes.c_uint32),('second',ctypes.c_uint32),('weight',ctypes.c_float)]
class Oracle:
 def __init__(self,private):
  self.lib=ctypes.CDLL(str(Path(private).parent/'kernel335/selection-oracle-private.so'))
  self.lib.choose.argtypes=[ctypes.POINTER(Region),ctypes.c_uint32,ctypes.c_float,ctypes.POINTER(Selection)]
  self.lib.blend.argtypes=[ctypes.POINTER(Data),ctypes.POINTER(Data),ctypes.c_float,ctypes.POINTER(Data)]
  self.lib.encode.argtypes=[ctypes.POINTER(Data),ctypes.c_uint32,ctypes.c_void_p]
 def evaluate(self,profile,kelvin,aec):
  coordinate=profile['reference_triggers'];hdr={'exposure_time_ratio':0,'sensitivity_ratio':2,'exposure_gain_ratio':4}[profile['hdr_control']];aecpos=0 if profile['aec_control']=='lux_index' else 2
  def visit(nodes,level):
   def child(node):return Data((ctypes.c_float*9)(*node['matrix']),(ctypes.c_int32*3)(*node['offsets'])) if level==4 else visit(node['children'],level+1)
   if level==2:return child(next(node for node in nodes if node['trigger'][0]==coordinate['led_index']))
   position=hdr if level==1 else aecpos if level==3 else 0
   value=kelvin if level==4 else aec if level==3 else coordinate['drc_gain' if level==0 else 'hdr_ratio']
   regions=(Region*len(nodes))(*(Region(*node['trigger'][position:position+2]) for node in nodes));chosen=Selection()
   self.lib.choose(regions,len(nodes),value,ctypes.byref(chosen));a=child(nodes[chosen.first])
   if chosen.first==chosen.second:return a
   b=child(nodes[chosen.second]);result=Data();self.lib.blend(ctypes.byref(a),ctypes.byref(b),chosen.weight,ctypes.byref(result));return result
  return self.encode(visit(profile['core'],0),profile['qfactor'])
 def encode(self,data,q):
  fields=(ctypes.c_uint16*26)();self.lib.encode(ctypes.byref(data),q,fields);assert list(fields[:13])==list(fields[13:])
  rgb=[0.]*9
  for i,rgbindex in enumerate([4,5,3,7,8,6,1,2,0]):rgb[rgbindex]=ctypes.c_int16(fields[i]).value/(1<<(7+q))
  abc=[fields[i*3+j]&0xfff for j in range(3) for i in range(3)]
  return struct.pack('<HHI13H3H',3,2,40,*abc,*[fields[9+i]&0x7ff for i in range(3)],fields[12],0,0,0),rgb
