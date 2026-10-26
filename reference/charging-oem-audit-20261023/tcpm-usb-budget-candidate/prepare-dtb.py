"""Add only the standard supply reference to the frozen fixed-sink native DTB."""
from pathlib import Path
import hashlib,json,shutil,struct,subprocess
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OLD=BASE/'tcpm-sink507-dtb-private-01/samurai-tcpm-sink507-native-private.dtb'
OUT=BASE/'tcpm-usb-budget508-dtb-private-01'
TC='/soc@0/spmi@c440000/pmic@2/typec@1500'
USB='/soc@0/spmi@c440000/pmic@2/usb-input@1300'
sha=lambda b:hashlib.sha256(b).hexdigest()
source=(REF/'kernel104/verify-firmware.py').read_text()
assert sha(source.encode())=='2e0b03aa3cf7ae7651e0b2e1153c1c5eb0cba3a3b41ef1d375c9b06358cb9d5d'
scope={};exec(compile(source.split('\ndt_audit=',1)[0],'verified-FDT-parser','exec'),scope)
parse=scope['fdt_nodes']
before=OLD.read_bytes();assert sha(before)=='42749cc80100765932bdb55e9b79b5f922734143e264efabae7039cbada9e226'
nodes=parse(before)
assert USB in nodes and TC in nodes and 'phandle' not in nodes[USB] and 'power-supplies' not in nodes[TC]
handles={struct.unpack('>I',v)[0] for props in nodes.values() for k,v in props.items() if k in ['phandle','linux,phandle']}
handle=max(handles)+1;assert handle<0xffffffff
assert not OUT.exists();OUT.mkdir();target=OUT/'samurai-usb-budget508-native-private.dtb';shutil.copyfile(OLD,target)
for node,prop in [(USB,'phandle'),(TC,'power-supplies')]:
 subprocess.run(['fdtput','-t','x',str(target),node,prop,format(handle,'x')],check=True)
after=parse(target.read_bytes());expected={k:dict(v) for k,v in nodes.items()}
expected[USB]['phandle']=struct.pack('>I',handle);expected[TC]['power-supplies']=struct.pack('>I',handle)
assert after==expected
result={'passed':True,'installed':False,'base_sha256':sha(before),'DTB_path':str(target),
 'DTB_sha256':sha(target.read_bytes()),'DTB_bytes':target.stat().st_size,
 'only_changes':{USB:{'phandle':handle},TC:{'power-supplies':handle}},
 'all_other_nodes_and_properties_exact':True,'sink_PDO_and_5V_policy_unchanged':True,
 'APSD_remains_disabled_for_trial':True,'phone_accessed':False}
(HERE/'dtb-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
