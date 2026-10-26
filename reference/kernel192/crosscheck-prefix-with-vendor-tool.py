"""Independent bounded cross-check using a trimmed analysis copy, never the source BIN."""
from pathlib import Path
import os,struct,shutil,subprocess,resource,signal,json,xml.etree.ElementTree as ET,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel192');work=Path('/home/cy122/x2pro-linux/parser-k192-prefix-r2');work.mkdir(mode=0o700)
old=Path('/home/cy122/x2pro-linux/parser-k117');schema=work/'api/sensor';schema.parent.mkdir(parents=True)
shutil.copytree(old/'api/sensor',schema)
ns={'x':'http://www.w3.org/2001/XMLSchema'}
tree=ET.parse(schema/'camxsensordriver.xsd');seq=tree.find("./x:complexType[@name='SensorDriverData']/x:sequence",ns)
assert seq is not None and [e.attrib.get('name') for e in list(seq)[:2]]==['module_version','slaveInfo']
for node in list(seq)[2:]:seq.remove(node)
ET.register_namespace('xs',ns['x']);tree.write(schema/'camxsensordriver.xsd',encoding='utf-8',xml_declaration=True)
source=old/'com.qti.sensormodule.sunny_imx471.bin';orig=source.read_bytes();b=bytearray(orig)
_,so,ss=struct.unpack_from('<QQQ',b,0xa0)
for off in range(so,so+ss,72):
 name=bytes(b[off+8:off+40]).split(b'\0')[0]
 if name==b'sensorDriverData':struct.pack_into('<Q',b,off+64,128)
 elif struct.unpack_from('<I',b,off+40)[0]==1:struct.pack_into('<I',b,off+40,0)
analysis=work/'imx471-prefix-analysis.bin';analysis.write_bytes(b)
dest=work/'xml';dest.mkdir()
for p in [work,*work.rglob('*')]:os.chown(p,1000,1000)
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
 resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
args=['stdbuf','-oL','-eL',str(old/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(analysis)]
with (out/'vendor-prefix-crosscheck-private.log').open('xb') as log:
 proc=subprocess.Popen(args,cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(old/'runtime/lib')),user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
 timed=False
 try:proc.wait(timeout=8)
 except subprocess.TimeoutExpired:
  timed=True;os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3)
assert source.read_bytes()==orig
xmls=list(dest.glob('*.xml'))
report=dict(stage=192,source_bin_unchanged=True,analysis_copy_only=True,root_prefix_bytes=128,exit_code=proc.returncode,timed_out=timed,xml_files=[p.name for p in xmls],process_waited=True)
(out/'vendor-prefix-crosscheck-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));print((out/'vendor-prefix-crosscheck-private.log').read_text()[-1600:])
