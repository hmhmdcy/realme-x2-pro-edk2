"""Measure whether the current single-pass request actually emits LTM DC work."""
from pathlib import Path
import ast,ctypes,hashlib,importlib.util,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
storage=module('storage284',HERE.parent/'kernel284/storage.py');kernel=storage.mounted_build().parent/'source354'
source=(kernel/'drivers/media/platform/qcom/camss/camss-icp-a5-ipe.c').read_text()
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text())
prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix+='\nstruct camss_a5_ipe_ltm_geometry {bool data_collection,image_processing,mask_filter;};\n'
functions=[]
for name in ['ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_ltm_striping','camss_a5_ipe_encode_bypass_striping']:
 match=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert match;functions.append(match[0])
(P/'current-stripe.c').write_text(prefix+'\n'.join(functions))
q=subprocess.run(['gcc','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(P/'current-stripe.c'),'-o',str(P/'current-stripe.so')],capture_output=True);assert not q.returncode,q.stderr.decode()
class Layout(ctypes.Structure):_fields_=[('width',ctypes.c_uint32),('height',ctypes.c_uint32),('stride',ctypes.c_uint32),('slice_height',ctypes.c_uint32),('uv_swap',ctypes.c_bool)]
class Io(ctypes.Structure):_fields_=[('input',Layout),('output',Layout),('port',ctypes.c_uint32)]
class Geometry(ctypes.Structure):_fields_=[('dc',ctypes.c_bool),('ip',ctypes.c_bool),('mask',ctypes.c_bool)]
native=ctypes.CDLL(str(P/'current-stripe.so'));encode=native.camss_a5_ipe_encode_ltm_striping
encode.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.POINTER(Io),ctypes.c_uint32,ctypes.POINTER(Geometry),ctypes.POINTER(ctypes.c_uint32)];encode.restype=ctypes.c_int
colour=ctypes.CDLL(str(P.parent/'kernel422/current-colour-codec.so'));iqencode=colour.camss_a5_ipe_encode_ltm_iq
iqencode.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];iqencode.restype=ctypes.c_int
assert (P.parent/'kernel422/codec422/colour.c').read_bytes()==(kernel/'drivers/media/platform/qcom/camss/camss-icp-a5-colour.c').read_bytes()
o=module('oracle404',HERE.parent/'kernel404/oracle.py');scope=dict(o.scope);exec(compile(o.text.replace('64 if off==48','96 if off==48'),'current-single-pass-fw','exec'),scope);prepare=scope['prepare']
packet=(P/'factory-contract-private.bin').read_bytes();assert len(packet)==6008;rows=[]
for w,h in [(640,480),(650,480)]:
 outputs=[]
 for dc in [0,1]:
  ltm=bytearray(packet[3208:]);struct.pack_into('<I',ltm,80,dc)
  buffers=[ctypes.create_string_buffer(x) for x in [packet[32:136],packet[136:3208],bytes(ltm)]]
  iq=ctypes.create_string_buffer(8944);assert not iqencode(iq,8944,o.r.f.DATA+0x40000,*buffers)
  out=ctypes.create_string_buffer(bytes([0xa7])*32768,32768);used=ctypes.c_uint32(0);layout=Layout(w,h,w,h,False);io=Io(layout,layout,8);geo=Geometry(dc,bool(struct.unpack_from('<I',ltm,84)[0]),bool(struct.unpack_from('<I',ltm,8)[0]))
  assert not encode(out,32768,ctypes.byref(io),2,ctypes.byref(geo),ctypes.byref(used));stripe=out.raw[:used.value]
  assert out.raw[used.value:]==bytes([0xa7])*(32768-used.value)
  _,job,cdm=prepare(stripe,w,h,8,2,iq.raw)
  for name,data in [('iq',iq.raw),('stripe',stripe),('job',job),('cdm',cdm)]:(P/f'coarse-width-{w}-dc-{dc}-{name}-private.bin').write_bytes(data)
  controls=[struct.unpack_from('<I',cdm,i+4)[0] for i in range(0,len(cdm)-4,4) if struct.unpack_from('<I',cdm,i)[0]==0x5c60]
  outputs.append((stripe,job,cdm,controls))
 a,b=outputs
 rows.append(dict(width=w,height=h,passes=struct.unpack_from('<I',a[0],20)[0],dc_flag_changes_striping=a[0]!=b[0],
  dc_flag_changes_job=a[1]!=b[1],dc_flag_changes_hardware_commands=a[2]!=b[2],command_bytes=len(a[2]),
  ltm_module_control_values_equal=a[3]==b[3],ltm_module_control_writes=len(a[3]),
  dc_work_not_demonstrated_by_flag=True))
r=dict(stage=424,current_native_kernel_serializer_functions=True,whole_retained_native_firmware_preparation=True,
 actual_main_profile_ltm_and_colour_gamma_program_used=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),rows=rows,
 data_collection_flag_does_not_create_coarse_pass=True,full_ltm_dc_not_implemented_by_current_single_pass_interface=True,
 original_iq_and_all_native_commands_kept_private=True,phone_accessed=False,passed=all(not x['dc_flag_changes_striping'] and not x['dc_flag_changes_job'] and not x['dc_flag_changes_hardware_commands'] and x['passes']==1 for x in rows))
(HERE/'coarse-gap-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
