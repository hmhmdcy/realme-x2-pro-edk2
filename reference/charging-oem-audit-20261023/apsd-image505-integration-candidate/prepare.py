"""Compose a same-kernel source profile from the checked existing components."""
from pathlib import Path
import ast,difflib,hashlib,importlib.util,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];ROOT=REF.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
s=importlib.util.spec_from_file_location('original_guard_actual505_source_composition',helper);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);BUILD=m.mounted_build();SOURCE=(BUILD/'source').resolve()
O=REF/'charging-oem-audit-20261023';SESSION=REF/'charging-session-20261023'
OLD=O/'apsd-pd5v-client-bridge-candidate';NATIVE=O/'dwc-vbus-budget-fence-candidate';CLIENT=O/'apsd-eud-route-client-candidate';ROUTE=O/'eud-route-provider-candidate';HANDOFF=O/'eud-route-handoff-candidate';PHY=O/'apsd-phy-withdrawal-candidate';PD=O/'pd5v-owner-context-r2';INPUT=O/'apsd-current-usb-integration-candidate'
for path in [CLIENT/'test-r2-result.json',CLIENT/'build-result.json',ROUTE/'build-r2-result.json',HANDOFF/'build-r2-result.json',INPUT/'build-result.json']:
 assert json.loads(path.read_bytes())['passed'],path
original={'core.c':'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf','core.h':'525c1d5d8d0e501f4a92ddd6232961542b5c04521f29a50b8acf9ee86c41373c','gadget.c':'9eec86e42945a786447e6a6548a25b495e29a01bed8e8fbfc13e02903e1ff0c5'}
sources={};merge={}
def add(target,path):
 assert target not in sources;sources[target]=dict(origin=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
with tempfile.TemporaryDirectory(prefix='samurai-505-merge-') as directory:
 for name,pin in original.items():
  base=SOURCE/'drivers/usb/dwc3'/name;assert sha(base)==pin
  files=[]
  for tag,path in [('APSD',OLD/name),('base',base),('native504',NATIVE/name)]:
   out=Path(directory)/(tag+'-'+name);out.write_bytes(path.read_text().encode());files.append(out)
  child=subprocess.run(['git','merge-file','--diff3','-p',*[str(p) for p in files]],capture_output=True)
  assert child.returncode==0 and not child.stderr and b'<<<<<<<' not in child.stdout,(name,child.returncode)
  target=HERE/name
  if target.exists():assert target.read_bytes()==child.stdout
  else:target.write_bytes(child.stdout)
  merge[name]=dict(common_base_sha256=pin,APSD_sha256=sha(OLD/name),native504_sha256=sha(NATIVE/name),merged_sha256=sha(target),line_endings_normalized_for_merge_only=True,conflicts=0)
  add('drivers/usb/dwc3/'+name,target)
mapping={
 'drivers/usb/dwc3/samurai-apsd-owner.c':CLIENT/'samurai-apsd-owner.c',
 'drivers/usb/dwc3/samurai-apsd-owner.h':CLIENT/'samurai-apsd-owner.h',
 'drivers/usb/dwc3/samurai-apsd-once.h':OLD/'samurai-apsd-once.h',
 'drivers/usb/dwc3/samurai-usb-input-decode.h':INPUT/'samurai-usb-input-decode.h',
 'include/linux/usb/samurai-apsd-backend.h':INPUT/'samurai-apsd-backend.h',
 'include/linux/usb/samurai-pd5v.h':OLD/'qcom_pmic_typec_5v.h',
 'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c':PHY/'phy-qcom-snps-femto-v2.c',
 'drivers/phy/qualcomm/phy-qcom-snps-femto-v2-window.h':PHY/'phy-qcom-snps-femto-v2-window.h',
 'drivers/usb/dwc3/phy-qcom-snps-femto-v2-window.h':PHY/'phy-qcom-snps-femto-v2-window.h',
 'drivers/tty/serial/eud.c':ROUTE/'eud.c',
 'drivers/tty/serial/eud_earlycon.c':ROUTE/'eud_earlycon.c',
 'drivers/tty/serial/eud-com-window.h':SESSION/'eud-runtime-window-candidate-r2/eud-com-window.h',
 'drivers/usb/misc/qcom_eud.c':ROUTE/'qcom_eud.c',
 'drivers/firmware/efi/efi.c':HANDOFF/'efi.c',
 'drivers/firmware/efi/samurai-eud-handoff.c':HANDOFF/'samurai-eud-handoff.c',
 'drivers/firmware/efi/samurai-eud-handoff.h':HANDOFF/'samurai-eud-handoff.h',
 'drivers/firmware/efi/samurai-eud-handoff-wire.h':HANDOFF/'samurai-eud-handoff-wire.h',
 'include/linux/firmware/samurai-eud-handoff.h':HANDOFF/'samurai-eud-handoff.h',
 'include/linux/firmware/samurai-eud-handoff-wire.h':HANDOFF/'samurai-eud-handoff-wire.h',
 'drivers/firmware/efi/samurai-eud-route.c':ROUTE/'samurai-eud-route.c',
 'drivers/firmware/efi/samurai-eud-route.h':ROUTE/'samurai-eud-route.h',
 'include/linux/usb/samurai-eud-route.h':ROUTE/'samurai-eud-route.h',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.c':PD/'qcom_pmic_typec.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.h':PD/'qcom_pmic_typec.h',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_5v.c':OLD/'qcom_pmic_typec_5v.c',
 'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_5v.h':OLD/'qcom_pmic_typec_5v.h',
 'drivers/usb/typec/tcpm/qcom/Makefile':PD/'Makefile',
}
for target,path in mapping.items():add(target,path)
generated={
 'drivers/usb/dwc3/Makefile':(SESSION/'apsd-session-owner-candidate/Makefile.fragment').read_text(),
 'drivers/usb/dwc3/Kconfig':(CLIENT/'Kconfig.fragment').read_text(),
 'drivers/firmware/efi/Kconfig':(HANDOFF/'Kconfig.fragment').read_text()+'\n'+(ROUTE/'Kconfig.fragment').read_text(),
 'drivers/firmware/efi/Makefile':(HANDOFF/'Makefile.fragment').read_text()+'\n'+(ROUTE/'Makefile.fragment').read_text(),
}
for target,extra in generated.items():
 original_path=SOURCE/target;data=original_path.read_text()+'\n'+extra;out=HERE/(target.replace('/','--')+'.candidate')
 if out.exists():assert out.read_text()==data
 else:out.write_text(data)
 add(target,out)
# Analyze all whole functions against both branches, rather than claiming
# that a conflict-free text merge alone proves PM correctness.
tree=ast.parse((ROUTE/'review-sources.py').read_text());scope={}
exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.Import(names=[ast.alias(name='re')])]+[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='bodies'],type_ignores=[])),'<checked-body-extractor>','exec'),scope)
bodies=scope['bodies'];function_review={}
for name in ['core.c','gadget.c']:
 b=bodies((SOURCE/'drivers/usb/dwc3'/name).read_text());a=bodies((OLD/name).read_text());n=bodies((NATIVE/name).read_text());v=bodies((HERE/name).read_text())
 changed_a={key for key in a if a.get(key)!=b.get(key)};changed_n={key for key in n if n.get(key)!=b.get(key)};overlap=changed_a&changed_n
 assert not set(a)-set(v) and not set(n)-set(v)
 for key in set(a)|set(n):
  if key not in overlap:assert v[key]==(a[key] if key in changed_a else n[key]),(name,key)
 function_review[name]=dict(APSD_changed_or_added=sorted(changed_a),native504_changed_or_added=sorted(changed_n),both_branches_changed=sorted(overlap),nonoverlap_functions_exact=True)
profile={'TYPEC':'y','USB_ROLE_SWITCH':'y','TYPEC_TCPM':'y','TYPEC_QCOM_PMIC':'y','USB_QCOM_EUD':'y','QCOM_SAMURAI_EUD_HANDOFF':'y','QCOM_SAMURAI_EUD_ROUTE':'y','USB_DWC3_SAMURAI_APSD_OWNER':'y','USB_DWC3_SAMURAI_APSD_PD5V_CLIENT':'y','USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT':'y'}
record=dict(prepared=True,schema='samurai-APSD-505-source-composition-v1',sources=sources,merges=merge,function_review=function_review,required_config=profile,
 builtin_producers='COM and earlycon already builtin; change qcom EUD to builtin so an older rootfs module cannot be the selected driver',
 external_input_module_sources={name:dict(origin=(INPUT/name).relative_to(ROOT).as_posix(),sha256=sha(INPUT/name)) for name in ['samurai-usb-input.c','samurai-usb-input-decode.h','samurai-apsd-input.inc','samurai-apsd-backend.h']},
 firmware_sources={name:dict(origin=(HANDOFF/name).relative_to(ROOT).as_posix(),sha256=sha(HANDOFF/name)) for name in ['PlatformBm.c.candidate','samurai-eud-handoff-wire.h']},
 candidate_DTB_prepared=False,kernel_or_firmware_built=False,installed=False,phone_accessed=False)
with (HERE/'composition.json').open('x') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(dict(prepared=True,kernel_sources=len(sources),functions=function_review,DTB_prepared=False)))
