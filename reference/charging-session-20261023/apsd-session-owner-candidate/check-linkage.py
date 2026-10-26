"""Inspect only new objects + existing private component objects; no link."""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=json.loads((HERE/'object-build-result.json').read_bytes())
assert build['passed'] and build['shared_unchanged']
out=Path(build['private_output'])
objects={n:out/n for n in ['core.o','gadget.o','samurai-apsd-owner.o']}
objects['eud-r2.o']=REF/'charging-session-20261023/eud-runtime-window-candidate-r2/object-build/eud.o'
objects['phy-window.o']=Path('/home/cy122/charging-management-20261023/apsd-phy-window-candidate/kbuild/drivers/phy/qualcomm/phy-qcom-snps-femto-v2.o')
eud=json.loads((REF/'charging-session-20261023/eud-runtime-window-candidate-r2/object-build-result.json').read_bytes())
assert sha(objects['eud-r2.o'])==eud['object_sha256']
for n in ['core.o','gadget.o','samurai-apsd-owner.o']:assert sha(objects[n])==build['objects'][n]
symbols={}
for n,p in objects.items():
    text=subprocess.check_output(['aarch64-linux-gnu-nm',str(p)],text=True)
    defs=set();undef=set()
    for line in text.splitlines():
        fields=line.split()
        if len(fields)==2 and fields[0]=='U':undef.add(fields[1])
        if len(fields)==3 and fields[1] in ['T','D','R','B']:defs.add(fields[2])
    symbols[n]=(defs,undef)
defs=set.union(*(x[0] for x in symbols.values()))
cross={s for _,u in symbols.values() for s in u if s.startswith(('dwc3_apsd_owner_','dwc3_gadget_window_','eud_com_quiet_','qcom_snps_hsphy_window_'))}
missing=sorted(cross-defs)
eud_refs=sorted({s for _,u in symbols.values() for s in u if 'eud' in s.lower()})
unrelated_eud=sorted(set(eud_refs)-{'eud_com_quiet_begin','eud_com_quiet_cancel','eud_com_quiet_end'})
result={'passed':not missing and not unrelated_eud,'method':'nm only; not final vmlinux link or hardware proof',
        'objects':{n:sha(p) for n,p in objects.items()},'cross_component_undefined':sorted(cross),
        'unresolved_cross_component':missing,'eud_symbol_references':eud_refs,
        'unrelated_eud_symbols':unrelated_eud,
        'config_requires_builtin':['USB_DWC3','SERIAL_EUD_CONSOLE','PHY_QCOM_USB_SNPS_FEMTO_V2','POWER_SUPPLY'],
        'full_usb_eud_distinct_actual_config':'CONFIG_USB_QCOM_EUD=m',
        'old_component_tests_rerun':False,'image_or_module_linked':False}
(HERE/'linkage-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
