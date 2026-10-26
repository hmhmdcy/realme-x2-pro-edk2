"""Export the stock module's IFE LSC roots using its retained data parser."""
from pathlib import Path
import json,os,resource,shutil,signal,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
raw=(P.parent/'kernel298/sunny-imx319-tuning-private.bin').read_bytes()
work=Path('/home/cy122/x2pro-linux/parser-k317-lsc-r1');assert not work.exists();work.mkdir(mode=0o700)
schema=work/'api/isp';schema.mkdir(parents=True);(work/'api/common').mkdir()
for source,target in [(P/'sources/lsc_3_4_0.xsd',schema/'lsc_3_4_0.xsd'),
 (P.parent/'kernel298/ispglobalelements.xsd-reference-private',schema/'ispglobalelements.xsd'),
 (P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd'),
 (P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',schema/'ParameterTuningTypes.xsd')]:shutil.copyfile(source,target)
table,count=struct.unpack_from('<II',raw,0x98)
sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,start,length=sections[0];analysis=bytearray(raw);selected=[]
for pos in range(start,start+length,72):
 uid=struct.unpack_from('<Q',raw,pos)[0]
 name=raw[pos+8:pos+40].split(b'\0')[0].decode();version=struct.unpack_from('<I',raw,pos+40)[0]
 if not version:continue
 if name=='lsc34_ife':selected.append(uid)
 else:struct.pack_into('<I',analysis,pos+40,0)
assert len(selected)==7
for _,offset,size in sections[1:]:assert analysis[offset:offset+size]==raw[offset:offset+size]
(work/'analysis.bin').write_bytes(analysis);dest=work/'xml';dest.mkdir()
for path in [work,*work.rglob('*')]:os.chown(path,1000,1000)
def limits():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,384*1024**2))
 resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
reader=Path('/home/cy122/x2pro-linux/parser-k117')
with (P/'factory-lsc-parser.log').open('xb') as log:
 child=subprocess.Popen(['stdbuf','-oL','-eL',str(reader/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(work/'analysis.bin')],
  cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,
  start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
 try:code=child.wait(timeout=40)
 except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=3)
files=list(dest.rglob('lsc34_ife.xml'));rows=[]
for path in files:
 tree=ET.parse(path)
 rows.append(dict(path=str(path.relative_to(dest)),golden_regions=len(tree.findall('.//lsc34_golden_rgn_data')),
  core_regions=len(tree.findall('.//lsc34_rgn_data')),
  gain_lengths=sorted(set(len((node.text or '').split()) for name in ['r_gain','gr_gain','gb_gain','b_gain'] for node in tree.findall('.//'+name)))))
report=dict(stage=317,parser_exit=code,selected_uids=selected,roots=len(files),xml=rows,
 source_original_unchanged=True,payload_and_mode_tree_unchanged=True,no_phone_operations=True,individual_values_applied=False)
(P/'factory-lsc-export-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
assert code==0 and len(files)==len(selected) and all(row['golden_regions'] and row['core_regions'] and row['gain_lengths']==[221] for row in rows)
