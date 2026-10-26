from pathlib import Path
import copy,ctypes,json,shutil,struct,subprocess,sys
import yaml
import host,storage
from oracle import LscOracle,ccm
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE='/work/libcamera/src/libcamera-v0.7.2';oracle=LscOracle(P)
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
relative=Path('/private/camss341-contract');stage=storage.SDK/str(relative).lstrip('/');stage.mkdir(mode=0o700,exist_ok=True);rows=[];cases=json.loads((P/'profiles-private.json').read_text())
if len(sys.argv)>1:cases={name:cases[name] for name in sys.argv[1].split(',')}
with storage.sdk_candidate():
 shutil.copyfile(HERE/'dynamic-lsc-contract.cpp',stage/'contract.cpp');flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include'];links=['-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
 q=subprocess.run(['chroot',str(storage.SDK),'g++',*flags,str(relative/'contract.cpp'),*links,'-o',str(relative/'contract')],capture_output=True);(P/'contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 env=['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base',str(relative/'contract'),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so']
 for name,row in cases.items():
  path=P/'profiles'/(name+'.yaml');profile=yaml.safe_load(path.read_text());item=row['item'];m=item['match'];mode=next(mode for mode in profile['modes'] if mode['match']==m);lsc=mode['lens_shading'];colour=mode['colour_correction'];size=[m['width'],m['height']]
  shutil.copyfile(path,stage/path.name);(stage/(path.name+'.stats')).write_bytes((P.parent/'kernel338/samples-r1'/('sample-'+item['model']+'-private.stats')).read_bytes())
  args=[str(relative/path.name),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],str(int(colour['enabled']))]
  q=subprocess.run([*env,*args],capture_output=True,timeout=120);(P/(name+'-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(name,q.stderr.decode()[-3500:]);assert b'DYNAMIC_LSC_CONTRACT_PASS' in q.stdout
  packets=[json.loads(line.split(' ',1)[1]) for line in q.stdout.decode().splitlines() if line.startswith('CCM_PACKET ')];states={};actual=bytearray();expected=bytearray();uploaded=omitted=0
  for packet in packets:
   raw=bytes.fromhex(packet['packet']);offset=8;blocks={}
   assert struct.unpack_from('<II',raw)==(1,len(raw)-8)
   while offset<len(raw):
    kind,flags,length=struct.unpack_from('<HHI',raw,offset);assert kind not in blocks and flags==2 and length%8==0;blocks[kind]=raw[offset:offset+length];offset+=length
   assert offset==len(raw)
   previous=states.get((packet['epoch'],packet['parent']));value=struct.unpack('<f',struct.pack('<I',packet['bits']))[0]
   if packet['kind']=='unity':wantedLsc=oracle.unity(lsc,size)
   elif packet['kind']=='fallback':wantedLsc=previous[0]
   else:wantedLsc=oracle.evaluate(lsc,packet['kelvin'],value,size)
   if 6 in blocks:
    assert blocks[6]==wantedLsc,(name,packet['revision'],'lsc',sum(a!=b for a,b in zip(blocks[6],wantedLsc)));uploaded+=1;actual.extend(blocks[6]);expected.extend(wantedLsc)
   else:assert previous and wantedLsc==previous[0],(name,packet['revision'],'omitted changed LSC');omitted+=1
   wantedCcm=None
   if colour['enabled']:
    if packet['kind']=='fallback':wantedCcm=previous[1]
    elif packet['kind'] in ['unity','manual']:
     matrix=[1,0,0,0,1,0,0,0,1] if packet['kind']=='unity' else [0,0,1,0,.75,0,1,0,0];wantedCcm=oracle.ccm.encode(ccm.Data((ctypes.c_float*9)(*matrix),(ctypes.c_int32*3)(0,0,0)),colour['qfactor'])
    else:wantedCcm=oracle.ccm.evaluate(colour,packet['kelvin'],value)
    assert blocks[3]==wantedCcm[0] and struct.pack('<9f',*packet['matrix'])==struct.pack('<9f',*wantedCcm[1]),(name,packet['revision'],'ccm');actual.extend(blocks[3]);expected.extend(wantedCcm[0])
   else:assert 3 not in blocks and packet['matrix']==[0]*9
   states[packet['epoch'],packet['revision']]=(wantedLsc,wantedCcm)
  assert uploaded>2 and omitted>0
  (P/(name+'-actual-private.bin')).write_bytes(actual);(P/(name+'-expected-private.bin')).write_bytes(expected);assert actual==expected
  result=dict(case=name,packets=len(packets),uploaded_lsc_blocks=uploaded,unchanged_lsc_omitted=omitted,compared_bytes=len(actual),differing_bytes=0,kind=row['kind'],ccm_enabled=colour['enabled'],passed=True);rows.append(result);print(json.dumps(result),flush=True)
report=dict(stage=341,actual_aarch64_ipa=True,pinned_lsc_interpolation_and_single_pair_calibration=True,independent_hermite_resampling=True,coalesced_lsc_ccm_wb_snapshots=True,delayed_sof_matrix_metadata=True,zero_cct_fallback=True,unchanged_lsc_not_reuploaded=True,cases=rows,default_profiles_changed=False,installed=False,passed=True)
filename='ipa-contract-validation.json' if len(sys.argv)==1 else 'ipa-contract-subset-validation.json';(HERE/filename).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=341,cases=len(rows),compared_bytes=sum(row['compared_bytes'] for row in rows),passed=True)))
