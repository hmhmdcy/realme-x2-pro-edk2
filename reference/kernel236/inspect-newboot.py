"""Read actual camera topology while the independent startup observer waits."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import json,os,subprocess
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
index=len(list(root.glob('k236-inspect-*')))
out=root/('k236-inspect-'+str(index));out.mkdir(mode=0o700)
report=dict(stage=236,inspection=index,taint=int(Path('/proc/sys/kernel/tainted').read_text()),sensors={},rails={},pmic={})
for node in Path('/sys/bus/i2c/devices').iterdir():
 compatible=node/'of_node/compatible'
 if compatible.exists():
  raw=compatible.read_bytes()
  kind='rear' if raw==b'realme,rmx1931-imx319\0' else 'front' if raw==b'sony,imx471\0' else None
  if kind:report['sensors'][kind]=dict(device=node.name,driver=(node/'driver').resolve().name if (node/'driver').is_symlink() else None,runtime=(node/'power/runtime_status').read_text().strip())
for name in ['1-0004','1-0008']:
 node=Path('/sys/bus/i2c/devices')/name
 report['pmic'][name]=dict(present=node.exists(),driver=(node/'driver').resolve().name if (node/'driver').is_symlink() else None)
for node in Path('/sys/class/regulator').glob('regulator.*'):
 name=(node/'name').read_text().strip()
 if not name.startswith(('cam-rear-','cam-front-')):continue
 fields={}
 for field in ['state','num_users','microvolts']:
  try:fields[field]=(node/field).read_text().strip()
  except OSError as error:fields[field]='errno:'+str(error.errno)
 report['rails'][name]=fields
report['loaded']={name:Path('/sys/module',name).exists() for name in ['qcom_pm8008','qcom_pm8008_imx319_lab','imx319','imx471','qcom_camss']}
report['remoteprocs']={(node/'name').read_text().strip():(node/'state').read_text().strip() for node in Path('/sys/class/remoteproc').glob('remoteproc*')}
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
report['faults']={name:log.count(value) for name,value in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()}
for name,path in [('ssc-state','/run/samurai-ssc/state.json'),('deferred','/sys/kernel/debug/devices_deferred'),('regulators','/sys/kernel/debug/regulator/regulator_summary'),('domains','/sys/kernel/debug/pm_genpd/pm_genpd_summary'),('clocks','/sys/kernel/debug/clk/clk_summary')]:
 p=Path(path)
 if p.exists():(out/(name+'-private.txt')).write_bytes(p.read_bytes())
for service in ['samurai-ssc','iio-sensor-proxy','samurai-gnss-watch','greetd','networkmanager']:
 result=subprocess.run(['rc-service',service,'status'],capture_output=True,timeout=10)
 (out/(service+'-status-private.log')).write_bytes(result.stdout+result.stderr)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=70)
report = json.loads(result.stdout)
(host.PRIVATE / ('inspection-' + str(report['inspection']) + '-host-private.json')).write_bytes(result.stdout)
print(json.dumps(report))
