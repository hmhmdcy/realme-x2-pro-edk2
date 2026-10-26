"""Recover the fifth sensor's exact cached sources; no phone or SDK operations."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,re,struct,subprocess,sys,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
BUILD=storage.mount.mounted_build()
P=Path('/mnt/e/edk2-samurai-out/kernel454');P.mkdir(mode=0o700,exist_ok=True)
tree=ast.parse((HERE.parent/'kernel450/inspect-lens-scope.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Description')
exec(compile(ast.Module(body=[node],type_ignores=[]),'retained450-description','exec'))
binary=P.parent/'kernel282/shine-ov02a1b-module-private.bin'
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='63e2122a9b0003ed8af6eade006e3a5ef7c40beb530fa0d5a6069836e9b3b5fa'
description=Description(binary)
w=description.words(description.one('sensorDriverData')[0])
ri=description.words(description.one('resolutionInfo')[0]);f=description.words(ri[3])
assert len(w)==102 and len(f)==32
rawmode=[]
for index,value in enumerate(f):
 rawmode.append(dict(index=index,u64=value,double=struct.unpack('<d',struct.pack('<Q',value))[0]))
(P/'resolution-words-private.json').write_text(json.dumps(rawmode,indent=2)+'\n')
source=P/'ov02a1b-realme-mono-source-private.c'
raw=source.read_bytes();blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+bytes([0])+b).hexdigest()
expected_blob='dcec857475355940d02122c9716ed4f9267bf112'
if blob(raw)!=expected_blob:
 assert raw.endswith(b'\n\n') and blob(raw[:-1])==expected_blob,'Downloaded public source must match pinned Git blob'
 source.write_bytes(raw[:-1]);raw=raw[:-1]
assert blob(raw)==expected_blob
manifest=dict(repository='realme-kernel-opensource/realme8_C25_C25s_Narzo30_Narzo50A_AndroidR_kernel_source',commit='a3e43e3d5cbd14caa5cc1a48561180bfc708dbb4',path='drivers/misc/mediatek/imgsensor/src/mt6853/camera_project/oppo6853/ov02a1b_mipi_mono/ov02a1bmipimono_Sensor.c',git_blob_sha1=expected_blob,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
(P/'public-source-manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
cached=P.parent/'kernel117/CamxChi/chi-cdk/api/sensor'
selected=[]
for path in cached.glob('*.xsd'):
 text=path.read_text()
 if 'lineLengthPixelClock' in text:
  for element in ET.fromstring(text).findall('{http://www.w3.org/2001/XMLSchema}complexType'):
   if element.attrib.get('name')=='ResolutionData':
    (P/(path.stem+'-resolution-schema-private.txt')).write_text(ET.tostring(element,encoding='unicode'))
    selected.append(dict(path=str(path),type='ResolutionData',schema_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
print(json.dumps(dict(source=manifest,mode_schema=selected,raw_mode_saved=True,no_phone_sdk=True),indent=2))
if '--clock-source' in sys.argv:
 repo=Path('/home/cy122/x2pro-linux/refs/CamxChi-k117');commit='9f17f1b568626b393e785b369c5dc94543774d7a'
 paths=set((P.parent/'kernel117/CamxChi/tree-paths.txt').read_text().splitlines())
 names=['camx/src/core/camximagesensordata.cpp','chi-cdk/api/sensor/camxsensordriverapi.h']
 assert all(name in paths for name in names),'Exact paths must exist in retained pinned inventory'
 clock_sources=[]
 for name in names:
  target=P/(Path(name).name+'-private')
  if not target.exists():
   result=subprocess.run(['git','-C',str(repo),'show',commit+':'+name],capture_output=True,timeout=20,env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
   (P/(Path(name).name+'-retrieval-private.log')).write_bytes(result.stderr)
   assert result.returncode==0,'Exact source not cached; use targeted pinned retrieval, never broad grep'
   target.write_bytes(result.stdout)
  content=target.read_bytes()
  expected=subprocess.check_output(['git','-C',str(repo),'rev-parse',commit+':'+name],text=True,env=dict(os.environ,GIT_NO_LAZY_FETCH='1')).strip()
  assert blob(content)==expected,'Private source must match pinned cached Git object'
  if name.endswith('.h'):assert blob(content)=='b44b87cc6ce6e611a23ad58b8e3a541780763fde'
  clock_sources.append(dict(path=name,commit=commit,git_blob_sha1=expected,sha256=hashlib.sha256(content).hexdigest()))
  lines=content.decode().splitlines()
  print('\n'.join(str(i+1)+': '+line for i,line in enumerate(lines) if re.search('GetVTPixelClk|vtPixelClk|GetLineReadoutTime|SensorFillExposureData|struct RegSetting',line))[:5500])
 cpp=(P/'camximagesensordata.cpp-private').read_text()
 assert 'pResData->lineLengthPixelClock * pResData->frameLengthLines * pResData->frameRate' in cpp
 assert '(lineLengthPixelClock * NanoSecondsPerSecond) / VTPixelClock' in cpp
 assert re.search(r'\.mclk\s*=\s*24\b',raw.decode()) and re.search(r'\.pclk\s*=\s*39000000\b',raw.decode())
 report=dict(stage=454,oem_sensor_description_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),public_sensor_source=manifest,clock_and_api_sources=clock_sources,mode_schema=selected,public_sensor_init_or_clock_not_copied=True,nominal_vt_clock_derived_from_oem_mode=True,output_pixel_clock_is_not_vt=True,actual_sensor_clock_verified=False,phone_or_sdk_accessed=False,passed=True)
 (HERE/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
