from pathlib import Path
import hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k194-module-abi';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k194-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert not any(b'sony,imx471' in p.read_bytes() or b'qcom,pm8008\0' in p.read_bytes() for p in Path('/sys/firmware/devicetree/base').rglob('compatible'))
stage=root/'k194-modules';imx=json.loads((stage/'imx471-modules-build-validation.json').read_text());pmic=json.loads((stage/'pmic-module-build-validation.json').read_text());records=[(Path(r['path']).name,Path(r['path']).stem.replace('-','_'),r['sha256']) for r in imx['modules']]+[('qcom-pm8008.ko','qcom_pm8008',pmic['module_sha256'])]
assert all(not Path('/sys/module/'+n).exists() and hashlib.sha256((stage/f).read_bytes()).hexdigest()==h for f,n,h in records)
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before);loaded=[];results=[]
try:
 for f,n,h in records:
  p=subprocess.run(['insmod',str(stage/f)],capture_output=True,timeout=15);results.append(dict(module=n,returncode=p.returncode,sha256=h));(out/(n+'-private.log')).write_bytes(p.stdout+p.stderr)
  if Path('/sys/module/'+n).exists():loaded.append(n)
  assert p.returncode==0 and n in loaded
finally:
 for n in reversed(loaded):subprocess.run(['rmmod',n],check=True,capture_output=True,timeout=15)
 (out/'attempts.json').write_text(json.dumps(results,indent=2)+'\n')
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after);delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
assert all(v==0 for v in delta.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='512' and all(not Path('/sys/module/'+n).exists() for f,n,h in records)
assert Path('/sys/firmware/devicetree/base/soc@0/cci@ac4b000/status').read_bytes()==b'disabled\0'
r=dict(stage=194,kernel_build=183,modules=results,all_load_and_unload_passed=True,no_matching_sensor_or_pmic_nodes=True,hardware_probe_exercised=False,fault_delta=delta,taint=512,installed_modules_unchanged=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
