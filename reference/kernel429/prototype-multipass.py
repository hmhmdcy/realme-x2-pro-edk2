"""Isolate native two-pass fields before changing the maintained submitter."""
from pathlib import Path
import ast,ctypes,importlib.util,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
kernel=module('storage284',HERE.parent/'kernel284/storage.py').mounted_build().parent/'source354'
source=(kernel/'drivers/media/platform/qcom/camss/camss-icp-a5-ipe.c').read_text()
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text())
prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix+='\nstruct camss_a5_ipe_ltm_geometry {bool data_collection,image_processing,mask_filter;};\n'
functions=[]
for name in ['ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_ltm_striping']:
 match=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert match;functions.append(match[0])
(P/'base-stripe.c').write_text(prefix+'\n'.join(functions))
subprocess.run(['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(P/'base-stripe.c'),'-o',str(P/'base-stripe.so')],check=True)
class Layout(ctypes.Structure):_fields_=[('width',ctypes.c_uint32),('height',ctypes.c_uint32),('stride',ctypes.c_uint32),('slice_height',ctypes.c_uint32),('uv_swap',ctypes.c_bool)]
class Io(ctypes.Structure):_fields_=[('input',Layout),('output',Layout),('port',ctypes.c_uint32)]
class Geometry(ctypes.Structure):_fields_=[('dc',ctypes.c_bool),('ip',ctypes.c_bool),('mask',ctypes.c_bool)]
lib=ctypes.CDLL(str(P/'base-stripe.so'));encode=lib.camss_a5_ipe_encode_ltm_striping
encode.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Io),ctypes.c_uint32,ctypes.POINTER(Geometry),ctypes.POINTER(ctypes.c_uint32)];encode.restype=ctypes.c_int
def candidate():
 w,h=640,480;qw,qh=160,120;layout=Layout(w,h,w,h,False);io=Io(layout,layout,8);geo=Geometry(True,True,True)
 out=ctypes.create_string_buffer(16384);used=ctypes.c_uint32();assert not encode(out,16384,ctypes.byref(io),2,ctypes.byref(geo),ctypes.byref(used))
 base=out.raw[:used.value];data=bytearray(len(base)+624)
 data[:24]=base[:24];struct.pack_into('<I',data,20,2)
 data[436:848]=base[24:436];data[2892:]=base[2268:]
 def h16(at,x):struct.pack_into('<H',data,at,x&65535)
 def w32(at,x):struct.pack_into('<I',data,at,x)
 def coarse_axis(at,length,output_length,horizontal):
  for off,value in [(32,1),(34,length-1),(36,65535),(38,1 if horizontal else 2),(42,24),(46,1),(64,3),(66,length-1),
   (84,27),(86,65536//27),(278,length-1),(282,length-1 if horizontal else length//2-1)]:h16(at+off,value)
  w32(at+60,(length<<21)//output_length)
  if horizontal:
   for off,value in [(72,1),(76,12),(80,output_length-1)]:h16(at+off,value)
 coarse_axis(24,qh,108,False)
 for off,value in [(352,qh-1),(390,1),(404,1)]:h16(24+off,value)
 w32(24+408,2248)
 h16(436+360,qh-1);w32(436+400,434);w32(436+408,2460)
 at=2268;h16(at+6,qw-1);h16(at+44,257);coarse_axis(at+48,qw,144,True);w32(at+600,qw*qh);w32(at+604,1)
 for i in range(2):
  at=2892+i*624;first,last=struct.unpack_from('<2H',data,at+20)
  h16(at+12,max(0,first//4-10));h16(at+14,min(qw-1,last//4+10))
 return bytes(data)
if __name__=='__main__':
 fw=module('firmware425',HERE.parent/'kernel425/firmware-model.py')
 config=(P.parent/'kernel425/width-640-dc-1-config-private.bin').read_bytes();iq=(P.parent/'kernel424/coarse-width-640-dc-1-iq-private.bin').read_bytes()
 expected=(P.parent/'kernel425/width-640-dc-1-stripe-private.bin').read_bytes();actual=candidate()
 model,job,cdm,meta=fw.prepare(config,actual,iq,640,480,46080)
 ejob=(P.parent/'kernel425/width-640-dc-1-job-private.bin').read_bytes();ecdm=(P.parent/'kernel425/width-640-dc-1-commands-private.bin').read_bytes()
 differences=[i for i,(a,b) in enumerate(zip(cdm,ecdm)) if a!=b]
 (P/'prototype-stripe-private.bin').write_bytes(actual);(P/'prototype-cdm-private.bin').write_bytes(cdm)
 (P/'prototype-differences-private.json').write_text(json.dumps([dict(offset=i,actual=cdm[i],expected=ecdm[i]) for i in differences],indent=2)+'\n')
 print(json.dumps(dict(candidate_bytes=len(actual),native_bytes=len(expected),job_equal=job==ejob,command_difference_bytes=len(differences),first_differences=differences[:30],scratch=meta['required_scratch_bytes'])))
