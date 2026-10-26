"""Assemble the thin disk-stage worker from pinned actual read/atomic helpers."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
UPDATE=REF/'charging-session-20261023/charger-reattach-observation-update-candidate/stage-worker.py'
STAGE=REF/'charging-ui-audit-20261023/usb-irq-protection-stage-candidate/stage-worker.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert sha(UPDATE.read_bytes())=='509cb3841e76cab5db6a62399717994920ab9623f609cc7cad6fb427f9aa6698'
assert sha(STAGE.read_bytes())=='47794e53b8f31e974a968cb6610c69a49e456042be940bca7104bb182595c83a'
u=UPDATE.read_text();s=STAGE.read_text();ut=ast.parse(u);st=ast.parse(s)
def item(text,tree,name,kind=ast.FunctionDef):
    return ast.get_source_segment(text,next(n for n in tree.body if isinstance(n,kind) and n.name==name))+'\n'
def method(name):
    tree=next(n for n in ut.body if isinstance(n,ast.ClassDef) and n.name=='Device')
    n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return '    '+ast.get_source_segment(u,n)+'\n'
def base_method(name):
    tree=next(n for n in ut.body if isinstance(n,ast.ClassDef) and n.name=='R8Device')
    n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return '    '+ast.get_source_segment(u,n)+'\n'
header='''"""One current-IRQ disk-only USB stage. Default source only; no child or module operation."""
from pathlib import Path
import argparse,base64,copy,fcntl,hashlib,io,json,math,os,re,runpy,stat,sys,tarfile,time,uuid
sys.dont_write_bytecode=True
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
VERSION='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
ROOT='/root/charging-management-20261023'
SERVICE='/usr/sbin/samurai-charging'
SERVICE_SHA='61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
SOC_SERIAL='/sys/devices/soc0/serial_number'
LOCK='/run/lock/samurai-charging.lock'
INSTANCE='/sys/devices/platform/samurai-gauge-protection'
MANIFEST='/usr/share/samurai-charging/manifest.json'
MODULE_ROOT='/lib/modules/'+RELEASE+'/extra/samurai-charging/'
KO=MODULE_ROOT+'samurai-mp2650.ko'
USB=MODULE_ROOT+'samurai-usb-input.ko'
ORDER=[USB,MANIFEST]
OLD='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
USB_OLD='7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f'
USB_NEW='d04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037'
PROVIDERS=('samurai-usb-input','samurai-gauge-protection')
NOTES={'samurai-usb-input':'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d',
       'samurai-gauge-protection':'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec',
       'samurai-mp2650':'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
MAC_CACHE_SHA='02c98143301bb5db896c6f535f490495428df8b8c6fd6ab3cdc69ca507a545a8'
CARRIERS={'boot':(100663296,'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'),
          'logdump':(67108864,'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1')}
'''
parts=[header]
for n in ['need','sha','detail','encode','read_owned','validate_lease']:parts.append(item(s,st,n))
for n in ['AtomicFailure']:parts.append(item(s,st,n,ast.ClassDef))
parts.append(item(s,st,'atomic_replace'))
parts.append(item(u,ut,'MutationUncertain',ast.ClassDef));parts.append(item(u,ut,'UnsafeSample',ast.ClassDef))
parts.append(item(u,ut,'safe_sample'))
# The actual old first definitions and current overriding definitions are both
# retained so their calls resolve identically, without carrying update code.
old_sample=next(n for n in ut.body if isinstance(n,ast.FunctionDef) and n.name=='_safe_sample')
old_healthy=next(n for n in ut.body if isinstance(n,ast.FunctionDef) and n.name=='healthy')
old_unchanged=next(n for n in ut.body if isinstance(n,ast.FunctionDef) and n.name=='unchanged')
for n in [old_sample,old_healthy,old_unchanged]:parts.append(ast.get_source_segment(u,n)+'\n')
parts.append('_r8_sample=_safe_sample\n_r8_healthy=healthy\n_r8_unchanged=unchanged\n')
for name in ['_safe_sample','healthy','unchanged']:
    n=[n for n in ut.body if isinstance(n,ast.FunctionDef) and n.name==name][-1]
    parts.append(ast.get_source_segment(u,n)+'\n')
parts.append(item(u,ut,'source_limits'));parts.append(item(u,ut,'stopped'))
pre=item(u,ut,'preflight')
pre=pre.replace('samurai-charger-reattach-preflight-v1','samurai-irq-native-usb-pm-preflight-v1').replace('unpack_request(request)','unpack(request)')
pre=pre.replace("sha(device.read_owned(KO)[0]) == OLD_CHARGER and device.read_owned(KO)[1] == 0o600", "sha(device.read_owned(USB)[0]) == USB_OLD and device.read_owned(USB)[1] == 0o600")
pre=pre.replace('old charger disk identity','current USB disk identity')
pre=pre.replace("eligible=mode == 'managed',\n                      reason=None if mode == 'managed' else 'full_state_not_restorable'", "eligible=True, reason=None")
parts.append(pre)
base_names=['read_owned','manager','manager_for_stop','verify','notes_match','registers','observe','manager_command','module_state']
parts.append('class SnapshotBase:\n'+''.join(base_method(n) for n in base_names))
current=['identity','board_client','verify_carriers','open_mac','mac_evidence','lock_existing','open_readonly','check_window','observe','close']
parts.append('class Device(SnapshotBase):\n'+''.join(method(n) for n in current)+(HERE/'device-body.py.inc').read_text())
parts.append((HERE/'stage-body.py.inc').read_text())
text='\n'.join(parts);compile(text,str(HERE/'stage-worker.py'),'exec')
(HERE/'stage-worker.py').write_text(text,encoding='utf-8',newline='\n')
result={'passed':True,'source_sha256':sha((HERE/'stage-worker.py').read_bytes()),'inputs':{str(p):sha(p.read_bytes()) for p in [UPDATE,STAGE]},
'stage_functions_exact':['need','sha','detail','encode','read_owned','validate_lease','AtomicFailure','atomic_replace'],
'current_snapshot_methods_exact':current,'base_read_methods_exact':base_names,
'subprocess_or_unload_or_start_method_included':False,'future_payload_pins_generated':False}
(HERE/'source-reuse.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
