"""Export all IFE BLS modes with the retained factory parser on a data-only copy."""
from pathlib import Path
import hashlib,json,os,resource,shutil,signal,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;OLD=P.parent/'kernel298'
source=OLD/'sunny-imx319-tuning-private.bin';raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='9c8609ec7d2d0e70bbbc3809209fb446af26105892aa56a97a242f1b40775196'
previous=json.loads((OLD/'bls-typed-crosscheck-private.json').read_text());assert previous['original_reader_one_ife_root_18_regions_exact']
work=Path('/home/cy122/x2pro-linux/parser-k299-bls-r3');assert not work.exists();work.mkdir(mode=0o700)
schema=work/'api/isp';schema.mkdir(parents=True);(work/'api/common').mkdir()
pins=[]
for src,dst in [(P.parent/'kernel297/bls_1_2_0.xsd-reference-private',schema/'bls_1_2_0.xsd'),(OLD/'ispglobalelements.xsd-reference-private',schema/'ispglobalelements.xsd'),(OLD/'globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),(P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',schema/'ParameterTuningTypes.xsd')]:
 shutil.copyfile(src,dst);pins.append(dict(name=dst.name,sha256=hashlib.sha256(src.read_bytes()).hexdigest(),bytes=src.stat().st_size))
table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,off,size=sections[0];data=bytearray(raw);allowed=set();selected=[];module_count=0
for pos in range(off,off+size,72):
 uid=struct.unpack_from('<Q',raw,pos)[0];name=raw[pos+8:pos+40].split(b'\0')[0].decode();version=struct.unpack_from('<I',raw,pos+40)[0]
 if not version:continue
 module_count+=1
 if name=='bls12_ife':
  assert version==0x20001 and struct.unpack_from('<I',raw,pos+44)[0]==0;selected.append(uid)
 else:
  # Clear only the packed major/minor in the analysis copy. Data and mode tree stay exact.
  struct.pack_into('<I',data,pos+40,0);allowed.update(range(pos+40,pos+44))
assert len(selected)==16 and all(i in allowed for i,(a,b) in enumerate(zip(raw,data)) if a!=b)
for _,off,size in sections[1:]:assert data[off:off+size]==raw[off:off+size]
analysis=work/'analysis.bin';analysis.write_bytes(data);dest=work/'xml';dest.mkdir()
for p in [work,*work.rglob('*')]:os.chown(p,1000,1000)
def limits():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(15,15));resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
reader=Path('/home/cy122/x2pro-linux/parser-k117');timed_out=False
with (P/'factory-bls-reader-private.log').open('xb') as log:
 child=subprocess.Popen(['stdbuf','-oL','-eL',str(reader/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(analysis)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
 try:ret=child.wait(timeout=20)
 except subprocess.TimeoutExpired:timed_out=True;os.killpg(child.pid,signal.SIGKILL);ret=child.wait(timeout=3)
files=list(dest.rglob('bls12_ife.xml'));fields=['offset','threshold_r','threshold_gr','threshold_gb','threshold_b'];rows=[]
for p in files:
 root=ET.parse(p).getroot();values=[[float(n.findtext(k)) for k in fields] for n in root.findall('.//bls12_rgn_data')]
 rows.append(dict(path=str(p.relative_to(dest)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),regions=len(values),unique_values=sorted(set(tuple(v) for v in values))))
private=dict(stage=299,terminal=True,exit=ret,timed_out=timed_out,selected_uids=selected,versioned_modules=module_count,files=rows,schemas=pins,source_unchanged=source.read_bytes()==raw,all_payload_and_mode_tree_sections_unchanged=True)
(P/'factory-bls-export-private.json').write_text(json.dumps(private,indent=2)+'\n')
assert ret==0 and not timed_out and len(files)==16 and all(r['regions']==18 and r['unique_values']==[(960.,0.,0.,0.,0.)] for r in rows),private
report=dict(stage=299,source_sha256=hashlib.sha256(raw).hexdigest(),source_bytes=len(raw),original_factory_reader_exit=ret,
 all16_ife_modes_exported=True,ife_regions=288,direct_decoder_ife_regions=previous['ife_regions'],direct_decoder_bps_regions=previous['bps_regions'],
 all_ife_offsets_u14=960,all_ife_thresholds_zero=True,independent_reader_and_direct_decoder_agree=True,
 schemas=pins,xml_files_sha256={r['path']:r['sha256'] for r in rows},
 source_and_payload_unchanged=True,analysis_copy_only_module_version_metadata_projected=True,
 original_mode_tree_preserved=True,selected_runtime_mode_not_yet_confirmed=True,individual_eeprom_calibration_not_obtained=True,
 full_factory_pipeline_not_recreated=True,no_phone_operation=True,no_factory_values_installed=True)
(HERE/'factory-bls-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
