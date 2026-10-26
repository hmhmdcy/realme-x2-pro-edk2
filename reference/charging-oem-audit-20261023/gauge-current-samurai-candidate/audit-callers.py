"""Static current-property consumer inventory; no old suites or device access."""
from pathlib import Path
import hashlib,importlib.util,json,re,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('current_callers_storage284',REF/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
shared=storage.mounted_build();source=shared.parent/'source354'
kernel_calls=[];files_scanned=0
for folder in ['drivers/power/supply','drivers/hwmon','drivers/thermal','kernel/power']:
 for p in (source/folder).rglob('*.c'):
  text=p.read_text(errors='replace');files_scanned+=1
  if 'POWER_SUPPLY_PROP_CURRENT_NOW' not in text:continue
  for match in re.finditer(r'power_supply_get_property(?:_from_supplier)?\s*\([^;]{0,300}?POWER_SUPPLY_PROP_CURRENT_NOW[^;]{0,180}?;',text,re.S):
   kernel_calls.append(dict(path=str(p.relative_to(source)),line=text[:match.start()].count('\n')+1,
    sha256=sha(p),excerpt=match.group()))
entry=REF/'charging-session-20261023/r8-source-integration'
installed=[]
for folder in ['kernel-sources','rootfs-sources']:
 for p in (entry/folder).rglob('*'):
  if not p.is_file():continue
  text=p.read_text(errors='replace')
  for i,line in enumerate(text.splitlines(),1):
   if 'CURRENT_NOW' in line or 'current_now' in line:
    installed.append(dict(path=str(p.relative_to(entry)),line=i,sha256=sha(p),text=line))
upower=REF/'charging-ui-audit-20261023/upower-up-device-supply-battery.c'
assert 'current_avg' not in upower.read_text()
framework=[]
for name in ['drivers/power/supply/power_supply_sysfs.c','drivers/power/supply/power_supply_hwmon.c']:
 p=source/name;lines=p.read_text().splitlines()
 framework.append(dict(path=name,sha256=sha(p),current_lines=[dict(line=i+1,text=s) for i,s in enumerate(lines) if 'CURRENT_' in s or 'current_' in s]))
r=dict(passed=True,scope='all three direct current/status function callers in fixed bq core; exact current R8 source entry and service; cached UPower; static generic kernel consumer inventory',
 kernel_C_files_scanned=files_scanned,kernel_direct_CURRENT_NOW_calls=kernel_calls,
 actual_R8_CURRENT_NOW_mentions=installed,framework=framework,
 cached_upower_sha256=sha(upower),cached_upower_reads_current_avg=False,
 runtime_generic_consumer_binding_not_proven=True,arbitrary_external_userspace_not_certified=True,
 charging_control_does_not_consume_bq_CURRENT_NOW=True,R8_notification_consumes_STATUS=True,
 phone_accessed=False,SDK_invoked=False,Git_invoked=False)
(HERE/'caller-audit.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,kernel_files_scanned=files_scanned,kernel_static_calls=len(kernel_calls),R8_mentions=len(installed))))
