from pathlib import Path
import ast,json

here=Path(__file__).resolve().parent
source=(here.parent/'kernel200/build-package.py').read_text()
def replace(old,new):
 global source
 assert old in source,old
 source=source.replace(old,new)
replace("out = Path('/mnt/e/edk2-samurai-out/kernel200')","out = Path('/mnt/e/edk2-samurai-out/kernel204')")
replace("dt = json.loads((ref.parent / 'kernel199/static-dtb-validation.json').read_text())","dt = json.loads((ref / 'uart-candidate-validation.json').read_text())")
replace("dtb = (out.parent / 'kernel199/sm8150-samurai-mmcx-static-private.dtb').read_bytes()","dtb = (out / 'sm8150-samurai-bt-wake-static-private.dtb').read_bytes()")
replace("assert sha(dtb) == '2e2f8e64319195f2d4af98b4cec1a83a2da31ed80a97c2b6afbf261b2e25d3e2'","assert sha(dtb) == dt['candidate_dtb_sha256']")
replace("before = (out.parent / 'kernel172/boot-partition-k172-headset.img').read_bytes()","before = (out.parent / 'kernel200/boot-partition-k200-mmcx.img').read_bytes()")
replace("assert sha(before) == '77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28'","assert sha(before) == '5109097b74aafd38838174f31fbff2d8c940977fdc4982658ebe86f671d1e1f0'")
replace("assert oldtree.keys() == newtree.keys()","assert set(oldtree) <= set(newtree)\nassert set(newtree)-set(oldtree)==set(dt['new_sleep_nodes'])")
replace("assert len(dt_changes) == 2 and sorted(n for p, n in dt_changes) == ['power-domain-names', 'power-domains'], dt_changes\nassert all(p == '/soc@0/camss@acb3000' for p, n in dt_changes)","assert len(dt_changes)==4 and {n for p,n in dt_changes}=={'interrupts','interrupts-extended','pinctrl-names','pinctrl-1'},dt_changes\nassert all(p=='/soc@0/geniqup@cc0000/serial@c8c000' for p,n in dt_changes)\nassert oldtree['/soc@0/camss@acb3000']==newtree['/soc@0/camss@acb3000']")
replace("boot_path = out / 'boot-partition-k200-mmcx.img'","boot_path = out / 'boot-partition-k204-bt-wake.img'")
replace('stage=200','stage=204')
replace("dtb_semantic_changes=[dict(node=p, property=n) for p, n in dt_changes],","dtb_semantic_changes=[dict(node=p, property=n) for p, n in dt_changes], new_sleep_nodes=dt['new_sleep_nodes'],")
ast.parse(source);(here/'build-package.py').write_text(source)
print('Prepared firmware-only DTB build with unchanged code and boot200 rollback checks.')
