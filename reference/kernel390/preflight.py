from pathlib import Path
import hashlib,json,re,shlex,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;prior=HERE.parent/'kernel389'
for leaf in ['source','intree-build','dt-build','binding','deployment-package','artifact']:assert json.loads((prior/(leaf+'-validation.json')).read_text())['passed']
image=P.parent/'kernel363/Image-k363-private';meta=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text());raw=image.read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['image_sha256']
archives=[]
for match in re.finditer(b'\x1f\x8b\x08',raw):
 try:
  dec=zlib.decompressobj(31);data=dec.decompress(raw[match.start():],64*1024*1024)
  if data.startswith((b'070701',b'070702')) and b'TRAILER!!!' in data:archives.append(data)
 except zlib.error:pass
assert len(archives)==1;b=archives[0];pos=0;names=[]
while pos+110<=len(b):
 h=b[pos:pos+110];assert h[:6] in [b'070701',b'070702'];values=[int(h[6+i*8:14+i*8],16) for i in range(13)];size,namesize=values[6],values[11]
 name=b[pos+110:pos+110+namesize-1].decode().removeprefix('./');start=(pos+110+namesize+3)&~3
 if name=='TRAILER!!!':break
 names.append(name);pos=(start+size+3)&~3
embedded=[n for n in names if n.endswith('.ko')];assert len(embedded)==3 and not any('camss' in n or 'videobuf' in n or 'mem2mem' in n for n in embedded)
manifest=json.loads((P.parent/'kernel389/module-stage-manifest-private.json').read_text());baseline=json.loads((P.parent/'kernel388/sg-runtime-baseline-private.json').read_text());boot=json.loads((prior/'build-package-validation.json').read_text())
code=r'''from pathlib import Path
import hashlib,json,os,subprocess
manifest=MANIFEST;baseline=BASELINE
sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert os.uname().release==manifest['release'] and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha('/dev/disk/by-partlabel/boot')==BOOT and sha('/dev/disk/by-partlabel/logdump')==LOGDUMP
for n,row in baseline.items():assert sha(row['path'])==row['file_sha256'] and sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==row['note_sha256']
root=Path('/var/lib/samurai/k390-deployment');assert not root.exists()
modroot=Path('/lib/modules')/manifest['release'];result={}
for row in manifest['modules']:
 p=modroot/row['target_relative'];result[row['name']]=dict(path=str(p.resolve()),exists=p.exists(),sha256=sha(p) if p.exists() else None)
firmware=Path(manifest['firmware']['target']);assert not firmware.exists()
assert not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_m2m','camss_icp_a5_boot_test','v4l2_mem2mem'])
assert Path('/sys/firmware/devicetree/base/soc@0/icp@ac10000/status').read_bytes()==b'disabled\0'
services={n:[] for n in ['pipewire','wireplumber','greetd','sscfserv','ModemManager']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in services and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':services[n].append(int(p.name))
 except OSError:pass
print(json.dumps(dict(modules=result,module_root=str(modroot.resolve()),services=services,root=str(root),rootfs_release=Path('/etc/samurai-rootfs-release').read_text(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 remoteprocs={p.name:dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')},
 battery={p.name:{n:(p/n).read_text().strip() for n in ['capacity','temp','status'] if (p/n).exists()} for p in Path('/sys/class/power_supply').iterdir() if (p/'type').read_text().strip()=='Battery'})))
'''.replace('MANIFEST',repr(manifest)).replace('BASELINE',repr(baseline)).replace('BOOT',repr(boot['rollback_boot_sha256'])).replace('LOGDUMP',repr(meta['logdump_sha256']))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=35);(P/'preflight-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
assert all(v=='suspended' for v in d['camera_pm'].values()) and all(len(d['services'][n])==1 for n in ['pipewire','wireplumber'])
report=dict(stage=390,same_378_guard=True,current_boot366_and_logdump365_match=True,old_camss_and_sg_loaded=True,original_firmware_target_absent=True,initramfs_camera_modules_absent=True,embedded_module_names=embedded,
 target_module_original_presence={n:r['exists'] for n,r in d['modules'].items()},camera_pm=d['camera_pm'],battery=d['battery'],candidate_not_installed=True,passed=True)
(HERE/'preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
