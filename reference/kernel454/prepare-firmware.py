"""Convert only this handset's cached fifth sensor tables to private firmware."""
from pathlib import Path
import ast,hashlib,importlib.util,json,struct
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
storage.mount.mounted_build()
P=Path('/mnt/e/edk2-samurai-out/kernel454');P.mkdir(mode=0o700,exist_ok=True)
tree=ast.parse((HERE.parent/'kernel450/inspect-lens-scope.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Description')
exec(compile(ast.Module(body=[node],type_ignores=[]),'retained450-description','exec'))
source=P.parent/'kernel282/shine-ov02a1b-module-private.bin'
source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha=='63e2122a9b0003ed8af6eade006e3a5ef7c40beb530fa0d5a6069836e9b3b5fa'
d=Description(source);w=d.words(d.one('sensorDriverData')[0]);ri=d.words(d.one('resolutionInfo')[0]);mode=d.words(ri[3])
init=d.words(d.one('initSettings')[0]);stream=d.words(mode[2])
assert mode[0]==4 and mode[11]==1 and stream[4:7]==(1600,1200,10)
tables=[d.regs(init[2],init[1]),d.regs(mode[19],mode[18]),d.regs(w[58],w[57]),d.regs(w[60],w[59])]
counts=[len(table) for table in tables];assert counts==[88,1,2,2]
encoded=bytearray(b'OV2B'+bytes([1,4,0,0])+struct.pack('<4H',*counts))
values=[]
for table in tables:
 rows=[]
 for record in table:
  assert record['operation']==0 and record['address_bytes']==record['value_bytes']==1
  assert len(record['values'])==len(record['delays_us'])==1
  address,value,delay=record['address'],record['values'][0],record['delays_us'][0]
  assert 0<=address<=255 and 0<=value<=255 and 0<=delay<=1000000
  encoded.extend(struct.pack('<BBHI',address,value,0,delay));rows.append((address,value,delay))
 values.append(rows)
offset=16;decoded=[]
for count in struct.unpack_from('<4H',encoded,8):
 decoded.append([(a,v,delay) for a,v,reserved,delay in struct.iter_unpack('<BBHI',encoded[offset:offset+count*8])]);offset+=count*8
assert decoded==values and offset==len(encoded)
output=P/'ov02a1b-1600x1200-private.bin';output.write_bytes(encoded)
(P/'firmware-tables-private.json').write_text(json.dumps(dict(source_sha256=source_sha,tables=values),indent=2)+'\n')
rate=struct.unpack('<d',struct.pack('<Q',mode[10]))[0]
report=dict(stage=454,source_sha256=source_sha,firmware_sha256=hashlib.sha256(encoded).hexdigest(),bytes=len(encoded),table_counts=counts,ordered_duplicates_pages_values_delays_preserved=True,round_trip_equal=True,monochrome_raw10=True,lanes=1,width=1600,height=1200,declared_fps=rate,metadata_derived_vt_clock_hz=int(mode[3]*mode[4]*rate),output_pixel_clock_not_used_as_vt=True,actual_clock_or_sensor_verified=False,group_hold_placeholders_not_reused_for_exposure=True,firmware_loader_not_integrated=True,no_phone_sdk=True,passed=True)
(HERE/'firmware-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
