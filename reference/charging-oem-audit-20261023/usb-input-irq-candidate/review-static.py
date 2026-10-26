"""Pure retained-source/FDT review; no kernel calls or device access."""
from pathlib import Path
import hashlib
import json
import struct

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=(HERE/'samurai-usb-input.c').read_text()
base=(HERE/'baseline-samurai-usb-input.c').read_text()
def function(text,name):
    anchor=text.index(name+'(');start=text.rfind('\n',0,anchor)+1
    begin=text.index('{',anchor);depth=1;i=begin+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]
names=['samurai_usb_read_status','samurai_usb_get_budget','samurai_usb_type',
       'samurai_usb_get_property','samurai_usb_set_property','samurai_usb_poll',
       'samurai_usb_stop','samurai_usb_suspend','samurai_usb_resume',
       'samurai_usb_retain_for_native_consumer','samurai_usb_parent_match','samurai_usb_exit']
unchanged={n:hashlib.sha256(function(source,n).encode()).hexdigest() for n in names}
assert all(function(source,n)==function(base,n) for n in names)
assert '.shutdown = samurai_usb_shutdown' in source
assert 'samurai_usb_stop(platform_get_drvdata(pdev));' in function(source,'samurai_usb_shutdown')
probe=function(source,'samurai_usb_probe')
assert probe.index('input->paused = true')<probe.index('samurai_usb_request_events')<probe.index('devm_power_supply_register')<probe.index('devm_add_action_or_reset')<probe.index('input->paused = false')

dtb=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb')
raw=dtb.read_bytes();header=struct.unpack('>10I',raw[:40])
magic,total,off,strings_off,_,version,_,_,strings_len,struct_len=header
assert magic==0xd00dfeed and total==len(raw) and version>=17
strings=raw[strings_off:strings_off+strings_len]
props={};stack=[];cursor=off
while cursor<off+struct_len:
    token=struct.unpack_from('>I',raw,cursor)[0];cursor+=4
    if token==1:
        end=raw.index(0,cursor);name=raw[cursor:end].decode();cursor=(end+4)&~3
        stack.append(name);props.setdefault('/'+'/'.join(stack[1:]),{})
    elif token==2:stack.pop()
    elif token==3:
        length,nameoff=struct.unpack_from('>II',raw,cursor);cursor+=8
        end=strings.index(0,nameoff);name=strings[nameoff:end].decode()
        props['/'+'/'.join(stack[1:])][name]=raw[cursor:cursor+length];cursor=(cursor+length+3)&~3
    elif token==4:pass
    elif token==9:break
    else:raise AssertionError(token)
spmi='/soc@0/spmi@c440000';pmic=spmi+'/pmic@2';typec=pmic+'/typec@1500'
assert props[spmi]['compatible']==b'qcom,spmi-pmic-arb\0'
assert props[spmi]['#interrupt-cells']==struct.pack('>I',4) and 'interrupt-controller' in props[spmi]
assert props[pmic]['compatible']==b'qcom,pm8150b\0qcom,spmi-pmic\0'
assert props[pmic]['reg']==struct.pack('>II',2,0)
assert props[typec]['status']==b'disabled\0'
assert 'interrupt-parent' not in props[pmic]
fragment=(HERE/'board-irq.fragment.dts').read_text()
assert '<0x2 0x13 0x4 IRQ_TYPE_EDGE_BOTH>' in fragment and '<0x2 0x13 0x6 IRQ_TYPE_EDGE_RISING>' in fragment
assert 'interrupt-names = "usbin-plugin", "usbin-src-change"' in fragment
references={p.name:sha(p) for p in (HERE/'source-reference').glob('*.c')}
result={'scope':'static source/FDT proof only; separate actual driver-function fixture/build receipts',
        'source_sha256':sha(HERE/'samurai-usb-input.c'),'baseline_sha256':sha(HERE/'baseline-samurai-usb-input.c'),
        'unchanged_actual_functions':unchanged,'unchanged_actual_function_count':len(unchanged),
        'probe_order_paused_request_publish_stop_action_unpause':True,
        'devres_inverse_order':'stop/cancel -> power_supply_unregister -> free IRQ pair -> free input',
        'normal_shutdown_existing_stop_registered':True,
        'current_embedded_DTB':{'path':str(dtb),'sha256':sha(dtb),'spmi_path':spmi,'pmic_path':pmic,
          'irq_cells':4,'controller_present':True,'PMIC_SID':2,'PMIC_reg_cells':[2,0],
          'TypeC_status':'disabled','PMIC_has_no_explicit_interrupt_parent':True},
        'source_references_sha256':references,
        'parent_walk':'of_irq_find_parent climbs usb-input -> PMIC(no interrupt-parent/#interrupt-cells) -> SPMI(#interrupt-cells=4)',
        'runtime_irq_lookup':'platform optional uses fwnode name -> OF name index -> of_irq_get -> real IRQ domain; not numeric Linux IRQ constants',
        'limits':['DT fragment not applied or compiled here; no real IRQ delivery/latency measurement.',
                  'Both missing optional IRQ lookups preserve legacy poll fallback; resource discovery errors can map to ENXIO in platform core.',
                  'An enabled exact DT node prevents register_board software duplicate in the intended single-node board tree; not a multi-provider discovery framework.',
                  'No new wake IRQ policy, APSD/PD/role/config writes or budget authorization are introduced.',
                  'No full-probe hardware/devres-race execution claim follows from static order and fake boundary cases.'],
        'review_source_sha256':sha(Path(__file__))}
(HERE/'review-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'unchanged_functions':len(unchanged),'embedded_DTB_sha256':sha(dtb),'review_sha256':sha(HERE/'review-result.json')}))
