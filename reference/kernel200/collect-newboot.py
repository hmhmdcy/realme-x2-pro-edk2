from pathlib import Path
import hashlib,json,os,struct,subprocess,time

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k200-runtime'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot!=(root/'k200-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
if out.exists():assert (out/'boot-id-private.txt').read_bytes()==boot
else:out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
hashes={}
for dev,label,size,digest in [
 ('sde11','boot',100663296,'5109097b74aafd38838174f31fbff2d8c940977fdc4982658ebe86f671d1e1f0'),
 ('sde32','logdump',67108864,'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'),
 ('sda2','persist',None,'7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3')]:
 path='/dev/'+dev;assert subprocess.check_output(['lsblk','-ndo','PARTLABEL',path],text=True).strip()==label
 if size:assert int(subprocess.check_output(['blockdev','--getsize64',path],text=True))==size
 value=subprocess.check_output(['sha256sum',path],text=True).split()[0];assert value==digest,label;hashes[label]=value
(out/'partition-hashes-private.json').write_text(json.dumps(hashes))
subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],check=True,stdout=(out/'nv-check-private.txt').open('wb'))
subprocess.run(['sha256sum','-c',str(root/'k200-deploy/paired-module-tree.sha256')],cwd=Path('/usr/lib/modules')/os.uname().release,check=True,stdout=(out/'module-tree-check-private.txt').open('wb'))
dt=Path('/sys/firmware/devicetree/base');cam=dt/'soc@0/camss@acb3000';cc=dt/'soc@0/clock-controller@ad00000'
domains=list(struct.unpack('>8I',(cam/'power-domains').read_bytes()));names=(cam/'power-domain-names').read_bytes()
assert names==b'ife0\0ife1\0top\0mmcx\0'
handle=int.from_bytes((cc/'phandle').read_bytes(),'big');rpmh=list(struct.unpack('>II',(cc/'power-domains').read_bytes()))
assert domains==[handle,2,handle,3,handle,0,*rpmh] and rpmh[1]==9
module=Path(subprocess.check_output(['modinfo','-n','qcom-camss'],text=True).strip())
assert hashlib.sha256(module.read_bytes()).hexdigest()=='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58'
if not Path('/sys/module/qcom_camss').exists():subprocess.run(['modprobe','qcom-camss'],check=True)
camdev=Path('/sys/bus/platform/devices/acb3000.camss');assert (camdev/'driver').resolve()==Path('/sys/bus/platform/drivers/qcom-camss')
quiesce=json.loads((root/'k200-quiesce/quiesce-validation.json').read_text())
assert quiesce['quiesce_audit_pass'] and quiesce['boot_id']==(root/'k200-baseline/boot-id-private.txt').read_text().strip() and quiesce['taint']==512
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
(out/'genpd-private.txt').write_bytes(Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_bytes())
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
r=dict(stage=200,new_boot_identity_verified=True,kernel_build=183,boot_partition_readback_exact=True,
 logdump183_and_persist_nv_unchanged=True,paired_module_tree_784_files_exact=True,camss_four_domains_exact=True,
 camss_bound_to_persistent_candidate=True,camss_runtime_status=(camdev/'power/runtime_status').read_text().strip(),
 previous_boot_full_quiesce_receipt_verified=True,remoteprocs=rp,
 uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 fault_counts=counts,of_overlay_property_memory_warnings=log.count(b'OF: overlay: WARNING: memory leak will occur'),
 modemmanager191_unchanged=hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc')
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
