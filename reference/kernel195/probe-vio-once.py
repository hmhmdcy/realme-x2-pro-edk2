from pathlib import Path
import hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k195-vio-lookup';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k195-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
dt=Path('/sys/firmware/devicetree/base');node=dt/'soc@0/rsc@18200000/regulators-1/ldo1';stage=root/'k195-modules';meta=json.loads((stage/'vio-helper-build-validation.json').read_text());module=stage/'samurai-vio-phandle.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()==meta['module_sha256']
reg=[p for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'of_node').exists() and (p/'of_node').resolve()==node];assert len(reg)==1;reg=reg[0]
def props():return {p.name:p.read_bytes().hex() for p in node.iterdir() if p.is_file()}
def state():return {n:(reg/n).read_text().strip() for n in ['state','microvolts','num_users']}
before_props=props();before_state=state();before_regulator_path=str(reg.resolve());assert before_state==dict(state='disabled',microvolts='1800000',num_users='0') and 'phandle' not in before_props
(out/'before-node-private.json').write_text(json.dumps(before_props,indent=2)+'\n');before_log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before_log)
report=dict(stage=195,before_state=before_state,attempts=[])
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args):
 p=subprocess.run(args,capture_output=True,timeout=20);report['attempts'].append(dict(action=args[0],returncode=p.returncode));(out/(args[0]+'-private.log')).write_bytes(p.stdout+p.stderr);save();return p
try:
 assert run(['insmod',str(module)]).returncode==0
 params=Path('/sys/module/samurai_vio_phandle/parameters');values={p.name:int(p.read_text()) for p in params.iterdir()};report['parameters']=values
 assert values['assigned_handle']>0 and values['supply_microvolts']==1800000
 report['during_state']=state();during=props();assert int.from_bytes(bytes.fromhex(during.pop('phandle')),'big')==values['assigned_handle'] and during==before_props
 assert (dt/'samurai-vio-lookup/vif-supply').read_bytes()==values['assigned_handle'].to_bytes(4,'big') and state()==before_state and str(reg.resolve())==before_regulator_path
 report['exact_of_supply_lookup_succeeded']=True;save()
finally:
 if Path('/sys/module/samurai_vio_phandle').exists():assert run(['rmmod','samurai_vio_phandle']).returncode==0
 report['after_state']=state();report['node_properties_restored']=props()==before_props;report['same_regulator_object']=str(reg.resolve())==before_regulator_path;report['temporary_consumer_removed']=not (dt/'samurai-vio-lookup').exists();save()
after_log=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after_log);report['fault_delta']={k:after_log.count(v)-before_log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};report['taint']=int(Path('/proc/sys/kernel/tainted').read_text());save()
assert report['node_properties_restored'] and report['same_regulator_object'] and report['temporary_consumer_removed'] and report['after_state']==report['before_state'] and all(v==0 for v in report['fault_delta'].values()) and report['taint']==512
print(json.dumps(dict(stage=195,module_sha256=meta['module_sha256'],**{k:v for k,v in report.items() if k!='stage'},regulator_enable_or_voltage_writes=False,helper_unloaded=True)))
