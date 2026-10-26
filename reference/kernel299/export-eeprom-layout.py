"""Decode the matching factory EEPROM read/calibration description offline."""
from pathlib import Path
import hashlib,json,os,resource,shutil,signal,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
inventory=json.loads((P.parent/'kernel298/oem-tuning-inventory-private.json').read_text())
expected=next(r for r in inventory['files'] if r['path']=='lib64/camera/com.qti.sensormodule.sunny_imx319.bin')
source=P.parent/'kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin';raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected['sha256']
work=Path('/home/cy122/x2pro-linux/parser-k299-eeprom-r1');assert not work.exists();work.mkdir(mode=0o700)
schema=work/'api/sensor';schema.mkdir(parents=True)
origin=P.parent/'kernel117/CamxChi/chi-cdk/api/sensor'
for name in ['camxeepromdriver.xsd','camxsensorcommon.xsd']:shutil.copyfile(origin/name,schema/name)
table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,off,size=sections[0];data=bytearray(raw);selected=[];allowed=set()
for pos in range(off,off+size,72):
 uid=struct.unpack_from('<Q',raw,pos)[0];name=raw[pos+8:pos+40].split(b'\0')[0].decode();version=struct.unpack_from('<I',raw,pos+40)[0]
 if not version:continue
 if name=='EEPROMDriverData':selected.append(uid)
 else:struct.pack_into('<I',data,pos+40,0);allowed.update(range(pos+40,pos+44))
assert len(selected)==1 and all(i in allowed for i,(a,b) in enumerate(zip(raw,data)) if a!=b)
for _,off,size in sections[1:]:assert data[off:off+size]==raw[off:off+size]
analysis=work/'analysis.bin';analysis.write_bytes(data);dest=work/'xml';dest.mkdir()
for p in [work,*work.rglob('*')]:os.chown(p,1000,1000)
def limits():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,384*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(15,15));resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
reader=Path('/home/cy122/x2pro-linux/parser-k117');timed_out=False
with (P/'eeprom-reader-private.log').open('xb') as log:
 child=subprocess.Popen(['stdbuf','-oL','-eL',str(reader/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(analysis)],cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(reader/'runtime/lib')),user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
 try:ret=child.wait(timeout=20)
 except subprocess.TimeoutExpired:timed_out=True;os.killpg(child.pid,signal.SIGKILL);ret=child.wait(timeout=3)
files=list(dest.rglob('*.xml'));report=dict(stage=299,terminal=True,exit=ret,timed_out=timed_out,source_sha256=expected['sha256'],source_matches_current_vendor_inventory=True,source_unchanged=source.read_bytes()==raw,selected_uids=selected,payload_and_mode_tree_unchanged=True,
 xml_files=[dict(path=str(p.relative_to(dest)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files],no_phone_operation=True,no_eeprom_or_otp_read_or_write=True)
(P/'eeprom-export-private.json').write_text(json.dumps(report,indent=2)+'\n')
assert ret==0 and not timed_out and len(files)==1,report
root=ET.parse(files[0]).getroot();(P/'imx319-eeprom-layout-private.xml').write_bytes(ET.tostring(root))
report['root_tag']=root.tag;report['top_level_elements']=[n.tag for n in root]
(HERE/'eeprom-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
