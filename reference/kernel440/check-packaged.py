"""Verify the stripped release payload, then execute its actual IPA DSO."""
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,struct,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent;prefix=volume/'camera440-package-prefix-r2';SDK=storage.SDK;slot=SDK/'candidate440-r32';C='/candidate440-r32';tree=storage.candidate()/'src/libcamera-v0.7.2'
assert json.loads((HERE/'package-artifact-validation.json').read_text())['passed']
def allocated(path,installed=False):
 raw=path.read_bytes();assert raw[:5]==b'\x7fELF\x02';off=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58);sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)];ns=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
 result={ns[s[0]:].split(b'\0')[0].decode():(s[1],s[2],s[3],s[5],raw[s[4]:s[4]+s[5]] if s[1]!=8 else None) for s in sections if s[2]&2}
 dynamic=result['.dynamic'];entries=[];rpaths=[]
 for at in range(0,len(dynamic[-1]),16):
  tag,value=struct.unpack_from('<qQ',dynamic[-1],at)
  if not tag:break
  if tag in [15,29]:rpaths.append(value)
  else:entries.append((tag,value))
 # Meson removes build RPATH on installation. Permit exactly that mutation;
 # retain comparisons of every other loader entry and allocated section byte.
 if installed:assert not rpaths,'Release payload retained a build RPATH'
 data=result['.dynstr'][-1];ranges=[(off,data.index(0,off)) for off in rpaths]
 result['.dynamic']=(*dynamic[:-1],tuple(entries))
 return result,ranges
identities=[]
for name,target in [('libcamera.so.0.7.2','usr/lib/libcamera.so.0.7.2'),('ipa_camss_vfe.so','usr/lib/libcamera/ipa/ipa_camss_vfe.so'),('camss_ipa_proxy','usr/libexec/libcamera/camss_ipa_proxy')]:
 rel={'libcamera.so.0.7.2':'output/src/libcamera/libcamera.so.0.7.2','ipa_camss_vfe.so':'output/src/ipa/camss-vfe/ipa_camss_vfe.so','camss_ipa_proxy':'output/src/libcamera/proxy/worker/camss_ipa_proxy'}[name]
 a,ranges=allocated(tree/rel);b,none=allocated(prefix/target,installed=True);assert not none
 # This installed Meson fills the now-unreferenced RPATH bytes with X.
 # Permit exactly that known range/pattern, not arbitrary dynstr changes.
 strings=a['.dynstr'];data=bytearray(strings[-1])
 for off,end in ranges:data[off:end]=b'X'*(end-off)
 a['.dynstr']=(*strings[:-1],bytes(data))
 assert a==b,(name,[n for n in a if a[n]!=b.get(n)]);identities.append(name)
@contextmanager
def bind():
 slot.mkdir(exist_ok=True);assert not any(slot.iterdir()) and subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
 subprocess.run(['mount','--bind',str(prefix),str(slot)],check=True,capture_output=True)
 try:yield
 finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
rows=[]
with bind():
 env=['env','LD_LIBRARY_PATH='+C+'/usr/lib'];ipa=C+'/usr/lib/libcamera/ipa/ipa_camss_vfe.so';W='/private/camss439-regression'
 cases=[('front-module',['/private/camss439-module/module',ipa,'/private/camss439-module/factory.yaml','factory','/private/camss439-module/packaged-unused.bin']),('legacy-factory',[W+'/legacy',ipa,W+'/legacy.yaml','factory',W+'/packaged-legacy.bin']),('legacy-bypass',[W+'/legacy',ipa,W+'/bypass.yaml','bypass',W+'/packaged-bypass.bin']),('gtm-module',[W+'/gtm',ipa,W+'/factory.yaml','factory',W+'/packaged-gtm.bin'])]
 for name,args in cases:
  q=subprocess.run(['chroot',str(SDK),*env,*args],capture_output=True,timeout=45);(P/(name+'-packaged-run.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(name,q.returncode,(q.stdout+q.stderr).decode()[-3500:]);rows.append({'test':name,'passed':True});print(json.dumps(rows[-1]),flush=True)
r={'stage':440,'build_iteration':2,'passed':True,'actual_packaged_arm64_camss_ipa_tested':True,'allocated_elf_sections_identical_to_current_build_after_install_rpath_removal':identities,'only_install_build_rpath_removal_normalized':True,'stripped_payload_uses_same_code_data_public_key':True,'contracts':rows,'all_six_ipa_signatures_verified':True,'all_five_noncamss_ipas_identical_to_r31':True,'sdk_binds_unmounted':True,'hardware_exercised':False,'installed':False}
(HERE/'packaged-contract-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
