"""Bind the offline helper, actual-function tests, build and sysfs contract."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
test=json.loads((HERE/'test-result.json').read_text())
build=json.loads((HERE/'build-result.json').read_text())
scope=HERE.parent/'apsd-lifecycle/start-on-cc-scope-r8/result.json'
assert sha(scope)=='7c39fcbadb22dd1e6678506bd4cbd6b5a8b8f3e68fd365620699521bcc0b96ea'
assert test['passed'] and test['group_count']==12
assert test['actual_module_functions']==12 and test['actual_core_functions']==7
assert build['passed'] and not build['diagnostic_lines']
assert build['shared_config_unchanged'] and build['shared_makefile_unchanged']
for n in ['samurai-usbin-init.c','usbin-init-core.h']:
 assert sha(HERE/n)==test['files'][n]==build['files'][n]
module=Path(build['module'])
assert sha(module)==build['module_sha256']
source=(HERE/'samurai-usbin-init.c').read_text()
assert source.count('regmap_update_bits(')==1
assert 'regmap_update_bits(((struct ui_device *)ctx)->map, UI_CFG, UI_BIT, value)' in source
assert not re.search(r'\bi2c_|0x1362|0x1341|EXPORT_SYMBOL',source)
fields=test['state_schema_fixture']
protocol=dict(schema=1,module_name='samurai_usbin_init',ko_name='samurai-usbin-init.ko',
 register_board=dict(type='bool',default=False,mode='0444',explicit_load_value=True),
 platform_device='samurai-usbin-init',state_path='/sys/bus/platform/devices/samurai-usbin-init/state',
 control_path='/sys/bus/platform/devices/samurai-usbin-init/control',state_mode='0444',control_mode='0200',
 commands=['arm','restore_saved','commit','cancel','observe'],
 phase_values=['observed','waiting','clear_verified','restored','committed','timeout','error','cancelled'],
 op_values={'0':'observe','1':'clear','2':'restore'},
 fields={n:('boolean' if isinstance(v,bool) else 'integer[8]' if isinstance(v,list) else 'string' if isinstance(v,str) else 'integer') for n,v in fields.items()},
 snapshot_arrays=['first','pre','post','saved'],snapshot_registers=['0x1307','0x1308','0x1310','0x1506','0x1509','0x150b','0x150d','0x1358'],
 off_predicate={'0x1310_mask':'0x10','0x150b_mask':'0x21','0x1509_mask':'0x20','each_masked_value':0},
 write=dict(address='0x1358',mask='0x80',clear_value=0,restore='same-instance saved actual masked bit only'),
 times=dict(clock='BOOTTIME milliseconds',poll_ms=250,stable_off_ms=500,prewrite_fresh_ms=250,window_ms=60000,
  basis='conservative engineering choices, not OEM timing requirements',
  deadline='fresh final gate rejects new write start at/after deadline; regmap completion is not hard-interrupted',
  zero_timestamp='checkpoint not reached; prewrite also exists for successful no-op',
  state_now='sampled before state mutex; host must bracket and reject stale observations'),
 state_read=dict(register_io=False,polling=False,control_side_effect=False),
 ready='same instance/boot, op=1, phase=waiting, armed/running true, fresh bracket, positive sufficient remaining_ms; host identity/guard also required',
 no_op='old_bit=0 clear_verified can have held_ref=false,pending_restore=false,can_unload=true; explicit commit records adoption',
 uncertainty='write error/readback/post failure after attempt retains pending_restore/selfref; no commit or automatic restore/unload',
 default_observe='one synchronous probe snapshot; no periodic work until explicit arm',
 unload_predicate='!running && !pending_restore && !held_ref; outcome/identity checks remain controller responsibilities',
 transaction='kernel instance discriminator only; external controller owns transaction/boot/guard and fetch-only unknown outcomes')
(HERE/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
names=['samurai-usbin-init.c','usbin-init-core.h','prepare-tests.py','test-init.c','run-tests.py',
 'tested-functions.inc','tested-struct.inc','function-manifest.json','test-result.json',
 'build-private.py','build-result.json','protocol.json','README.md','seal-delivery.py']
r=dict(passed=True,status='frozen offline review candidate',files={n:sha(HERE/n) for n in names},
 module_path=str(module),module_sha256=sha(module),oem_scope_result_sha256=sha(scope),
 actual_function_test_groups=12,actual_module_functions=12,actual_core_functions=7,
 compiled_in_tree=True,kernel='7.3.0-rc6-rmx1931-samurai-k363+',warnings=[],
 write_scope={'address':'0x1358','mask':'0x80','default':'no write','arm':'off-only clear','restore':'off-only actual saved bit','commit':'zero register IO'},
 physical_validation=False,phone_accessed=False,ssh_executed=False,usb_accessed=False,sdk_invoked=False,
 shared_source_modified=False,shared_build_modified=False,image_or_package_built=False,
 controller_included=False,limits=['no atomic physical detach guarantee','no hard realtime regmap completion deadline','no online write-safety proof','no icon/CDP/500mA success claim','no full live concurrency proof'])
(HERE/'delivery.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'passed':True,'delivery_sha256':sha(HERE/'delivery.json'),'module_sha256':sha(module),'protocol_sha256':sha(HERE/'protocol.json')}))
