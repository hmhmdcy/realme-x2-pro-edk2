from pathlib import Path
import json,struct
O=Path('/mnt/e/edk2-samurai-out/kernel91')
ns={};exec(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel91/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
a=ns['fdt_nodes']((O/'firmware-before.dtb').read_bytes());b=ns['fdt_nodes']((O/'firmware-after.dtb').read_bytes())
assert set(b)-set(a)=={'/reserved-memory/rmtfs-dynamic'}
assert set(a)-set(b)==set()
assert all(a[p]==b[p] for p in a)
n=b['/reserved-memory/rmtfs-dynamic']
assert set(n)=={'compatible','size','alignment','alloc-ranges','no-map','qcom,client-id','qcom,use-guard-pages','qcom,vmid'}
assert n['compatible']==b'qcom,rmtfs-mem\0'
assert struct.unpack('>II',n['size'])==(0,0x202000)
assert struct.unpack('>I',n['qcom,vmid'])==(15,)
assert struct.unpack('>IIII',n['alloc-ranges'])==(0,0xc0000000,0,0x30000000)
(O/'dtb-validation.json').write_text(json.dumps({'only_addition':'/reserved-memory/rmtfs-dynamic','original_nodes_byte_identical':True,'usable_bytes':0x200000,'guard_bytes':0x2000,'client':1,'vmid':15,'mpss_manual_start_preserved':True},indent=2)+'\n')
