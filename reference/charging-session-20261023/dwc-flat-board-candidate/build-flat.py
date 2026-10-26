"""Native9271 USB-only flat DT construction and full raw-property comparison.

One unique private dtc output. No kernel source edit, Image or carrier build.
"""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import textwrap
import time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
BASE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb')
OUT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/dwc-flat-board-private-01')
FIXED_SOURCE = Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01/source354')
PARSER = REF/'charging-ui-audit-20261023/usb-input-irq-board-candidate/inspect-dtb.py'
OLD = '/soc@0/usb@a6f8800'
CHILD = OLD+'/usb@a600000'
NEW = '/soc@0/usb@a600000'
DTC = Path('/usr/bin/dtc')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
cells = lambda *values: struct.pack('>'+str(len(values))+'I',*values)
strings = lambda *values: b''.join(s.encode()+b'\0' for s in values)


def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def block(text,name):
    match = re.search(r'(?m)^(\t*)'+re.escape(name)+r' \{',text)
    assert match,name
    end,depth = text.index('{',match.start())+1,1
    while depth:
        depth += (text[end]=='{')-(text[end]=='}')
        end += 1
    assert text[end:end+1]==';'
    return match.start(),end+1,match.group(1)


def render(name,raw,indent):
    if not raw:
        return indent+name+';\n'
    if name in {'compatible','status','clock-names','interrupt-names','interconnect-names',
                'phy-names','dr_mode','usb-psy-name'}:
        assert raw.endswith(b'\0')
        value=', '.join(json.dumps(s.decode()) for s in raw[:-1].split(b'\0'))
    else:
        assert len(raw)%4==0,name
        value='<'+ ' '.join(hex(n) for n in struct.unpack('>'+str(len(raw)//4)+'I',raw))+'>'
    return indent+name+' = '+value+';\n'


def main():
    if sys.flags.optimize or os.name=='nt':
        raise RuntimeError('explicit nonoptimized native Linux host dtc required')
    assert not OUT.exists(),'Unique output only; follow the original handle, never replay'
    assert sha(BASE)=='9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
    assert sha(PARSER)=='5280e01c3c662408d6dc60b65317208e76ed765dc86f64f1ac8698146ff9e5fd'
    assert sha(DTC)=='438747895b91454385a7acebac7e8f0a28f980c5b3fa2d5f3f2034d29b9120af'
    binding=FIXED_SOURCE/'Documentation/devicetree/bindings/usb/qcom,snps-dwc3.yaml'
    assert sha(binding)=='d6f619e153675f5bc5e66f7e142d14e4f570c839ca9d23f3a9649a6a165b727b'
    common=FIXED_SOURCE/'Documentation/devicetree/bindings/usb/snps,dwc3-common.yaml'
    controller=FIXED_SOURCE/'Documentation/devicetree/bindings/usb/usb-drd.yaml'
    spec=importlib.util.spec_from_file_location('frozen_native_fdt_decoder',PARSER)
    decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
    original=BASE.read_bytes();before=decoder.decode(original);nodes=before['nodes']
    assert len(nodes)==965 and sum(map(len,nodes.values()))==3965
    assert OLD in nodes and CHILD in nodes and NEW not in nodes
    assert not any(k in nodes[p] for p in [OLD,CHILD] for k in ['phandle','linux,phandle'])
    assert nodes[OLD]['compatible']==strings('qcom,sm8150-dwc3','qcom,dwc3')
    assert nodes[CHILD]['compatible']==strings('snps,dwc3')
    assert nodes[CHILD]['interrupts']==cells(0,133,4)
    parent=CHILD
    while 'interrupt-parent' not in nodes[parent]:
        assert parent!='/', 'Missing actual inherited interrupt controller'
        parent=parent.rsplit('/',1)[0] or '/'
    intc=nodes[parent]['interrupt-parent'];assert intc==cells(1)
    assert nodes[OLD]['clocks']==cells(0x2e,0x0c,0x2e,0xac,0x2e,5,0x2e,0xb0,0x2e,0xae,0x2e,0xbb)
    assert nodes[CHILD]['phys']==cells(0xca,0xcb,0)
    assert nodes[CHILD]['iommus']==cells(0x2d,0x140,0)
    assert nodes[CHILD]['usb-psy-name']==strings('samurai-usb-input')
    flat=dict(nodes[OLD])
    for name in ['#address-cells','#size-cells','ranges','dma-ranges']:
        del flat[name]
    for name,raw in nodes[CHILD].items():
        if name not in {'compatible','reg','interrupts'}:
            assert name not in flat,name
            flat[name]=raw
    flat['compatible']=strings('qcom,sm8150-dwc3','qcom,snps-dwc3')
    flat['reg']=cells(0,0x0a600000,0,0x100000)
    flat['interrupts-extended']=intc+nodes[CHILD]['interrupts']+nodes[OLD]['interrupts-extended']
    flat['interrupt-names']=strings('dwc_usb3')+nodes[OLD]['interrupt-names']
    expected={p:dict(props) for p,props in nodes.items() if p!=OLD and not p.startswith(OLD+'/')}
    expected[NEW]=flat
    relocated={}
    for path,props in nodes.items():
        if path.startswith(CHILD+'/'):
            dest=NEW+path[len(CHILD):]
            expected[dest]=dict(props);relocated[path]=dest
    assert len(expected)==964
    tracked={str(BASE):sha(BASE),str(PARSER):sha(PARSER),str(DTC):sha(DTC),str(binding):sha(binding)}
    OUT.mkdir(parents=True)
    phases=[]
    error=None

    def run(label,argv):
        started=time.monotonic();parent_error=None
        with (OUT/(label+'.stdout')).open('wb') as stdout,(OUT/(label+'.stderr')).open('wb') as stderr:
            child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
            try:
                save(OUT/'current-process.json',dict(pid=child.pid,argv=argv,phase=label,terminal=False))
                print(json.dumps(dict(phase=label,pid=child.pid)),flush=True)
            except BaseException as exc:
                parent_error=repr(exc)
            finally:
                rc=child.wait()
        phase=dict(phase=label,pid=child.pid,argv=argv,terminal=True,returncode=rc,
                   parent_error=parent_error,seconds=time.monotonic()-started,
                   stdout_sha256=sha(OUT/(label+'.stdout')),stderr_sha256=sha(OUT/(label+'.stderr')))
        phases.append(phase);save(OUT/'phases.json',phases);save(OUT/'current-process.json',phase)
        assert rc==0 and parent_error is None,phase

    try:
        run('decompile-original',[str(DTC),'-I','dtb','-O','dts','-o',str(OUT/'native-original-private.dts'),str(BASE)])
        dts=(OUT/'native-original-private.dts').read_text()
        start,end,indent=block(dts,'usb@a6f8800')
        old_block=dts[start:end]
        cs,ce,_=block(old_block,'usb@a600000')
        child_block=old_block[cs:ce]
        ps,pe,_=block(child_block,'ports')
        ports=textwrap.indent(textwrap.dedent(child_block[ps:pe]),indent+'\t')
        new_block=indent+'usb@a600000 {\n'+''.join(render(k,v,indent+'\t') for k,v in flat.items())
        new_block+='\n'+ports+'\n'+indent+'};'
        candidate=dts[:start]+new_block+dts[end:]
        (OUT/'native-flat-private.dts').write_text(candidate)
        (HERE/'native-flat-only.patch').write_text(''.join(difflib.unified_diff(dts.splitlines(True),candidate.splitlines(True),
            fromfile='native9271.dts',tofile='native-flat.dts')),newline='\n')
        target=OUT/'samurai-dwc-flat-private.dtb'
        run('compile-flat',[str(DTC),'-I','dts','-O','dtb','-o',str(target),str(OUT/'native-flat-private.dts')])
        after=decoder.decode(target.read_bytes());fresh=after['nodes']
        assert set(fresh)==set(expected)
        assert fresh==expected,'Every non-USB and relocated property must equal its original raw bytes'
        for key in ['reserves','boot_cpu','version','last_version']:
            assert before[key]==after[key],key
        assert fresh[NEW]['interrupt-names']==strings('dwc_usb3','pwr_event','hs_phy_irq','dp_hs_phy_irq','dm_hs_phy_irq','ss_phy_irq')
        assert fresh[NEW]['clock-names']==strings('cfg_noc','core','iface','sleep','mock_utmi','xo')
        phandles={int.from_bytes(props['phandle'],'big'):path for path,props in fresh.items() if 'phandle' in props}
        irqraw=fresh[NEW]['interrupts-extended'];irqcells=list(struct.unpack('>'+str(len(irqraw)//4)+'I',irqraw))
        irqs=[]
        while irqcells:
            ph=irqcells.pop(0);provider=phandles[ph]
            size=int.from_bytes(fresh[provider]['#interrupt-cells'],'big')
            value=irqcells[:size];del irqcells[:size]
            irqs.append(dict(provider=provider,phandle=ph,specifier=value))
        assert [x['specifier'] for x in irqs]==[[0,133,4],[0,130,4],[0,131,4],[9,3],[8,3],[6,4]]
        assert fresh[NEW+'/ports/port@1/endpoint']['phandle']==cells(0xc2)
        assert fresh[NEW+'/ports/port@1/endpoint']['remote-endpoint']==cells(0xcc)
        assert fresh['/soc@0/phy@88e8000/ports/port@1/endpoint']['remote-endpoint']==cells(0xc2)
        assert not any(OLD.encode() in raw for props in fresh.values() for raw in props.values())
        run('decompile-flat',[str(DTC),'-I','dtb','-O','dts','-o',str(OUT/'native-flat-readback-private.dts'),str(target)])
        olddiag=(OUT/'decompile-original.stderr').read_text()
        newdiag=(OUT/'decompile-flat.stderr').read_text()
        normalized_old=olddiag.replace(str(BASE),'<DTB>').replace(CHILD,NEW)
        normalized_new=newdiag.replace(str(target),'<DTB>')
        diagnostic_diff=list(difflib.unified_diff(normalized_old.splitlines(),normalized_new.splitlines()))
        save(OUT/'diagnostic-difference.json',diagnostic_diff)
        unchanged={path:props for path,props in nodes.items() if path!=OLD and not path.startswith(OLD+'/')}
        assert all(fresh[path]==props for path,props in unchanged.items())
        validators=dict(dt_validate_path=shutil.which('dt-validate'),
                        python_dtschema_present=importlib.util.find_spec('dtschema') is not None)
        binding_text=binding.read_text()
        assert 'qcom,sm8150-dwc3' in binding_text and 'const: qcom,snps-dwc3' in binding_text
        result=dict(passed=True,private_output=str(OUT),candidate_DTB_path=str(target),
            candidate_DTB_sha256=sha(target),candidate_DTB_bytes=target.stat().st_size,
            baseline_DTB_sha256=sha(BASE),baseline_DTB_bytes=len(original),
            old_nodes=len(nodes),new_nodes=len(fresh),old_properties=sum(map(len,nodes.values())),
            new_properties=sum(map(len,fresh.values())),outside_USB_nodes_checked=len(unchanged),
            all_non_USB_properties_raw_identical=True,all_relocated_ports_properties_raw_identical=True,
            exact_expected_tree_raw_equal=True,relocated_paths=relocated,
            removed_wrapper=OLD,old_child=CHILD,new_controller=NEW,
            old_wrapper_raw_properties={k:v.hex() for k,v in nodes[OLD].items()},
            old_child_raw_properties={k:v.hex() for k,v in nodes[CHILD].items()},
            new_controller_raw_properties={k:v.hex() for k,v in flat.items()},
            actual_IRQs=irqs,six_clock_raw_unchanged=True,IOMMU_stream_0x140_unchanged=True,
            PHY_supply_GPIO_camera_PMIC_EUD_TypeC_non_USB_raw_unchanged=True,
            C2_CC_graph_preserved=True,native_supply_name_preserved=True,
            reserve_table_bootcpu_FDT_versions_unchanged=True,
            normalized_decompile_diagnostics_equal=not diagnostic_diff,diagnostic_difference=diagnostic_diff,
            original_diagnostic_lines=len(olddiag.splitlines()),candidate_diagnostic_lines=len(newdiag.splitlines()),
            fixed_binding_sha256=sha(binding),schema_validation_run=False,existing_validator_capabilities=validators,
            binding_shape_review='SM8150 compatible, six clocks, six named IRQs, flat common DWC properties; no schema-pass claim',
            usb_psy_name_declared_directly_in_fixed_binding='usb-psy-name:' in binding_text,
            usb_psy_name_declared_directly_in_fixed_common='usb-psy-name:' in common.read_text(),
            phases=phases,inputs_before=tracked,inputs_after={p:sha(Path(p)) for p in tracked},
            script_sha256=sha(HERE/'build-flat.py'),patch_sha256=sha(HERE/'native-flat-only.patch'),
            DWC_source_config_Image_boot_rootfs_module_changed=False,
            device_SSH_USB_PM_storage_helper_SDK_Git_used=False)
        assert result['inputs_before']==result['inputs_after']
        save(OUT/'dt-result.json',result);save(HERE/'dt-result.json',result)
        print(json.dumps({k:result[k] for k in ['passed','candidate_DTB_sha256','candidate_DTB_bytes','old_nodes','new_nodes',
            'all_non_USB_properties_raw_identical','C2_CC_graph_preserved','normalized_decompile_diagnostics_equal',
            'existing_validator_capabilities']}),flush=True)
    except BaseException as exc:
        error=repr(exc)
        failed=dict(passed=False,error=error,phases=phases,private_output=str(OUT),
            input_baseline_unchanged=sha(BASE)==tracked[str(BASE)],script_sha256=sha(HERE/'build-flat.py'))
        save(OUT/'failure-result.json',failed);save(HERE/'failure-result.json',failed)
        print(json.dumps(dict(passed=False,error=error)),flush=True)
        raise


if __name__=='__main__':
    main()
