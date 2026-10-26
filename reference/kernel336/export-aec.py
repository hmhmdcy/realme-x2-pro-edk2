"""Export only retained Metering/Arbitration roots with the stock parser."""
from pathlib import Path
import json,os,shutil,struct,subprocess,sys,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
names=sys.argv[1:] or ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']
reports=[]
# The retained bins use Arbitration1.0.0 (176 bytes), while the public1.0.1
# appends disableBandingGainCapping. Keep payload intact and remove only that
# appended schema field. The independent decoder checks every old root slot.
ns={'s':'http://www.w3.org/2001/XMLSchema'}
schema_tree=ET.parse(P/'sources/aecArbitration.xsd');sequence=schema_tree.getroot().find('s:complexType[@name="AECCoreArbitrationType"]/s:sequence',ns)
field=sequence.find('s:element[@name="disableBandingGainCapping"]',ns);assert field is not None;sequence.remove(field)
revision=sequence.find('s:element[@name="module_version"]/s:complexType/s:attribute[@name="incr_revision"]',ns);assert revision.get('fixed')=='1';revision.set('fixed','0')
ET.register_namespace('xs',ns['s']);schema_tree.write(P/'sources/aecArbitration-1.0.0-inferred.xsd',encoding='utf-8',xml_declaration=True)
for name in names:
 index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
 analysis=bytearray(raw);table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
 start,length=sections[0][1:];roots=[]
 for pos in range(start,start+length,72):
  uid=struct.unpack_from('<Q',raw,pos)[0];tag=raw[pos+8:pos+40].split(b'\0')[0].decode();version=struct.unpack_from('<I',raw,pos+40)[0]
  if tag in ['Metering','Arbitration'] and version:roots.append(dict(uid=uid,tag=tag,bytes=index['entries'][str(uid)]['bytes']))
  else:struct.pack_into('<I',analysis,pos+40,0)
 work=Path('/home/cy122/x2pro-linux')/('parser-k336-'+name+'-aec-r2');schema=work/'api/stats/aec';dest=work/'xml'
 if not work.exists():
  schema.mkdir(parents=True,mode=0o700);(work/'api/common').mkdir();dest.mkdir()
  for file in ['aecMetering.xsd','aecArbitration.xsd','aecglobalelements.xsd']:shutil.copyfile(P/'sources'/file,schema/file)
  shutil.copyfile(P/'sources/aecArbitration-1.0.0-inferred.xsd',schema/'aecArbitration.xsd')
  shutil.copyfile(P.parent/'kernel298/globalelements.xsd-reference-private',work/'api/common/globalelements.xsd')
  shutil.copyfile(P.parent/'kernel117/CamxChi/chi-cdk/api/chromatix/XSD/ParameterTuningTypes.xsd',schema/'ParameterTuningTypes.xsd')
  (work/'analysis.bin').write_bytes(analysis)
  for file in [work,*work.rglob('*')]:os.chown(file,1000,1000)
 else:assert (work/'analysis.bin').read_bytes()==analysis
 exitfile=P/(name+'-parser-r2-exit.json');reader=Path('/home/cy122/x2pro-linux/parser-k117')
 if not exitfile.exists():
  with (P/(name+'-parser-r2.log')).open('xb') as log:
   child=subprocess.Popen(['stdbuf','-oL','-eL',str(reader/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(work/'analysis.bin')],cwd=work,
    env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
   code=child.wait(timeout=55)
  exitfile.write_text(json.dumps(dict(exit_code=code))+'\n')
 else:code=json.loads(exitfile.read_text())['exit_code']
 assert not code,(name,code)
 exported={tag:list(dest.rglob(tag+'.xml')) for tag in ['Metering','Arbitration']}
 assert {tag:len(rows) for tag,rows in exported.items()}=={tag:sum(r['tag']==tag for r in roots) for tag in exported}
 reports.append(dict(name=name,roots=roots,exported={tag:[str(p.relative_to(dest)) for p in rows] for tag,rows in exported.items()},payload_unchanged=True))
 print(json.dumps(dict(name=name,root_count=len(roots),export_counts={tag:len(rows) for tag,rows in exported.items()})),flush=True)
(P/'factory-aec-export-private.json').write_text(json.dumps(reports,indent=2)+'\n')
