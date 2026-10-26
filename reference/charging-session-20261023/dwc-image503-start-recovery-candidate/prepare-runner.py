"""Derive the 8-object/Image503 private runner from frozen actual run-502.

Generation/check only. The resulting runner has an explicit execute mode.
"""
from pathlib import Path
import difflib
import hashlib
import json

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OLD=REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
PREV=HERE.parent/'dwc-device-start-recovery-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=json.loads((OLD/'delivery.json').read_text())
assert previous['passed']
for n,h in previous['files'].items():assert sha(OLD/n)==h,n
original=(OLD/'run-502.py').read_text()
text=original


def replace(old,new):
    global text
    assert text.count(old)==1,(old,text.count(old))
    text=text.replace(old,new,1)


replace('"""Private Image502 from passed 501: BQ callback only, no boot packaging/device."""',
        '"""Private consistent DWC Image503 from passed 502; no boot packaging/device."""')
replace("PREVIOUS=REF/'charging-session-20261023/gauge-image501-repro-candidate'",
        "PREVIOUS=REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate'")
replace("BASE=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01')",
        "BASE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')")
replace("OUT=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')",
        "OUT=Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01')")
replace("FROZEN=HERE.parent/'gauge-notify-immediate-candidate/bq27xxx_battery.c'",
        "FROZEN=HERE.parent/'dwc-device-start-recovery-candidate'\n"
        "DWC_SOURCES={'drivers/usb/dwc3/gadget.c':'ca4bf1c5a1afa42267d2f7f8b636dfe7ca5a1b9581307093f93a892e2f004314',\n"
        "             'drivers/usb/dwc3/core.h':'9a8dc48a1283db17b6a0cad01f0bc43ff916cfa7dc3a11b680c2145984f97a67'}\n"
        "DWC_TARGETS=['drivers/usb/dwc3/'+n+'.o' for n in ['core','trace','gadget','ep0','debugfs',\n"
        "             'dwc3-qcom','dwc3-qcom-legacy','dwc3-generic-plat']]")
start=text.index('def check_local():')
end=text.index('\ndef prove_additional(',start)
old=text[start:end]
new='''def check_local():
    assert not sys.flags.optimize, 'Non-optimized interpreter required'
    pins = '''+repr({
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/delivery.json':sha(OLD/'delivery.json'),
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json':sha(OLD/'build-result.json'),
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/abi-reuse-result.json':sha(OLD/'abi-reuse-result.json'),
 'charging-session-20261023/dwc-device-start-recovery-candidate/delivery.json':sha(PREV/'delivery.json'),
 'charging-oem-audit-20261023/dwc-device-start-recovery-independent-review/review-result.json':sha(REF/'charging-oem-audit-20261023/dwc-device-start-recovery-independent-review/review-result.json'),
 'charging-session-20261023/dwc-start-recovery-image-integration-plan/delivery.json':sha(HERE.parent/'dwc-start-recovery-image-integration-plan/delivery.json'),
 })+'''
    for name,digest in pins.items(): assert sha(REF/name)==digest,name
    for leaf in [PREVIOUS,FROZEN]:
        delivery=json.loads((leaf/'delivery.json').read_bytes())
        assert delivery['passed']
        for name,digest in delivery['files'].items(): assert sha(leaf/name)==digest,name
    for name,digest in DWC_SOURCES.items(): assert sha(FROZEN/Path(name).name)==digest,name
    assert sha(HERE/'metadata-proof.py')==METADATA_SHA
'''
text=text[:start]+new+text[end:]
replace("    allowed={'.tmp_vmlinux1.kallsyms.o','.tmp_vmlinux2.kallsyms.o','drivers/power/supply/bq27xxx_battery.o',\n             'init/version.o','init/version-timestamp.o','vmlinux.o'}\n    assert {r['path'] for r in delta}==allowed, delta",
        "    metadata={'.tmp_vmlinux1.kallsyms.o','.tmp_vmlinux2.kallsyms.o','init/version.o','init/version-timestamp.o','vmlinux.o'}\n"
        "    changed={r['path'] for r in delta}\n"
        "    assert changed <= set(DWC_TARGETS)|metadata, delta\n"
        "    assert metadata <= changed, delta")
replace("==[REL]\n    def exports(path):", "==sorted(DWC_SOURCES)\n    def exports(path):")
replace("'compared_to':'actual passed Image501 repro'", "'compared_to':'actual passed Image502 notify'")
replace("    assert not diagnostics, diagnostics\n    return {'passed':True,",
        "    assert not diagnostics, diagnostics\n"
        "    object_log=(OUT/'B-dwc-eight-objects.log').read_text(errors='replace')\n"
        "    actual_compiles={n:len(re.findall(r'-c -o '+re.escape(n)+r'(?=\\s)',object_log)) for n in DWC_TARGETS}\n"
        "    assert all(count==1 for count in actual_compiles.values()),actual_compiles\n"
        "    save(OUT/'eight-compile-proof.json',actual_compiles)\n"
        "    return {'passed':True,'eight_actual_compile_commands':actual_compiles,")
replace("'actual_ELF_export_names_exact_501':True,'builtin_export_rows_exact_501':True,\n            'Module_symvers_exact_501':True,'public_headers_unchanged':True,",
        "'actual_ELF_export_names_exact_502':True,'builtin_export_rows_exact_502':True,\n"
        "            'Module_symvers_exact_502':True,'public_headers_unchanged':True,\n"
        "            'private_dwc_core_h_changed':True,'all_eight_dependency_targets_requested':True,")
replace("env.update(KBUILD_BUILD_VERSION='502',", "env.update(KBUILD_BUILD_VERSION='503',")
replace("        run('B-bq-object',argv+['drivers/power/supply/bq27xxx_battery.o'])", "        run('B-dwc-eight-objects',argv+DWC_TARGETS)")
replace("        assert [r['path'] for r in leaf_delta]==['drivers/power/supply/bq27xxx_battery.o','init/version.o']",
        "        changed_leaf={r['path'] for r in leaf_delta}\n"
        "        assert changed_leaf <= set(DWC_TARGETS)|{'init/version.o'},leaf_delta\n"
        "        assert 'init/version.o' in changed_leaf and 'drivers/usb/dwc3/gadget.o' in changed_leaf,leaf_delta\n"
        "        assert all(after[n]==original[n] for n in leaves if n not in set(DWC_TARGETS)|{'init/version.o'})")
replace("assert '#502 SMP PREEMPT '", "assert '#503 SMP PREEMPT '")
replace("            'arch/arm64/boot/Image','vmlinux','System.map','vmlinux.symvers','drivers/power/supply/bq27xxx_battery.o','init/version-timestamp.o']}",
        "            'arch/arm64/boot/Image','vmlinux','System.map','vmlinux.symvers','drivers/power/supply/bq27xxx_battery.o',\n"
        "            'init/version.o','init/version-timestamp.o',*DWC_TARGETS]}")
replace("assert outputs['arch/arm64/boot/Image']['sha256']!='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'",
        "assert outputs['arch/arm64/boot/Image']['sha256']!='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'")
text=text.replace("len(leaves)-2", "len(leaves)-9")
replace("'module_files_written':False,'B_default_false_unchanged':True,'bootargs_changed':False,",
        "'module_files_written':False,'B_default_false_unchanged':True,'bootargs_changed':False,\n"
        "                'dwc_sources':DWC_SOURCES,'dwc_dependency_targets':DWC_TARGETS,'pm_unwind_complete':False,")
replace("    assert sha(FROZEN)==B_SHA", "    assert all(sha(FROZEN/Path(n).name)==h for n,h in DWC_SOURCES.items())")
replace("    assert sha(BASE/'source354'/REL)=='0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe'",
        "    assert sha(BASE/'source354'/REL)==B_SHA\n"
        "    scope=json.loads((HERE.parent/'dwc-start-recovery-image-integration-plan/dependency-result.json').read_bytes())\n"
        "    assert set(scope['required_object_targets'])==set(DWC_TARGETS)\n"
        "    for row in scope['core_h_dependencies']:\n"
        "        assert sha(BASE/'build'/row['cmd_path'])==row['cmd_sha256']\n"
        "        assert sha(BASE/'build'/row['target'])==row['object_sha256']\n"
        "        assert sha(BASE/'source354'/row['source_path'])==row['source_sha256']\n"
        "    assert sha(BASE/'source354/drivers/usb/dwc3/core.h')=='525c1d5d8d0e501f4a92ddd6232961542b5c04521f29a50b8acf9ee86c41373c'")
replace("    shared_names=['.config','Module.symvers','arch/arm64/boot/Image','vmlinux','drivers/power/supply/bq27xxx_battery.o']",
        "    shared_names=['.config','Module.symvers','arch/arm64/boot/Image','vmlinux','drivers/power/supply/bq27xxx_battery.o',*DWC_TARGETS]\n"
        "    shared_source_names=[SOURCE/'drivers/usb/dwc3'/n for n in ['core.c','core.h','gadget.c','Makefile']]\n"
        "    shared_source_before={str(p):sha(p) for p in shared_source_names}")
replace("'KBUILD_BUILD_VERSION':'502'", "'KBUILD_BUILD_VERSION':'503'")
replace("'source_commit_base':base.COMMIT,'frozen_B_source_sha256':B_SHA,'default_parameter':False}",
        "'source_commit_base':base.COMMIT,'frozen_B_source_sha256':B_SHA,'default_parameter':False,\n"
        "              'dwc_sources':DWC_SOURCES,'dwc_dependency_targets':DWC_TARGETS}")
replace("        (OUT/'source354'/REL).write_bytes(FROZEN.read_bytes())\n        assert sha(OUT/'source354'/REL)==B_SHA",
        "        for n,h in DWC_SOURCES.items():\n"
        "            (OUT/'source354'/n).write_bytes((FROZEN/Path(n).name).read_bytes())\n"
        "            assert sha(OUT/'source354'/n)==h\n"
        "        assert sha(OUT/'source354'/REL)==B_SHA")
replace("        assert source_changes==[REL],source_changes\n        save(OUT/'source-delta.json',{'only_changed_file':REL,'before':snapshots['source354'][REL],\n                                    'after':source_now[REL]})",
        "        assert sorted(source_changes)==sorted(DWC_SOURCES),source_changes\n"
        "        save(OUT/'source-delta.json',{n:{'before':snapshots['source354'][n],'after':source_now[n]} for n in DWC_SOURCES})")
replace("str(HERE/'run-502.py')", "str(HERE/'run-503.py')")
replace("        shared_after={n:sha(BUILD/n) for n in shared_names}",
        "        shared_after={n:sha(BUILD/n) for n in shared_names}\n"
        "        shared_source_after={str(p):sha(p) for p in shared_source_names}")
replace("and parent_mounts_unchanged and shared_before==shared_after and original363_before==original363_after,",
        "and parent_mounts_unchanged and shared_before==shared_after and shared_source_before==shared_source_after and original363_before==original363_after,")
replace("'shared_before':shared_before,'shared_after':shared_after,'shared_critical_inputs_unchanged':shared_before==shared_after,",
        "'shared_before':shared_before,'shared_after':shared_after,'shared_critical_inputs_unchanged':shared_before==shared_after,\n"
        "                'shared_source_before':shared_source_before,'shared_source_after':shared_source_after,\n"
        "                'shared_sources_unchanged':shared_source_before==shared_source_after,")
replace("assert sys.argv[1:]==['--execute-502'],'Explicit --execute-502 required'",
        "assert sys.argv[1:]==['--execute-503'],'Explicit --execute-503 required'")
metadata=(OLD/'metadata-proof.py').read_text().replace("OLD_ID=b'#501 ","OLD_ID=b'#502 ").replace("NEW_ID=b'#502 ","NEW_ID=b'#503 ")
(HERE/'metadata-proof.py').write_text(metadata,newline='\n')
text=text.replace("DWC_TARGETS=['drivers", "METADATA_SHA="+repr(sha(HERE/'metadata-proof.py'))+"\nDWC_TARGETS=['drivers",1)
compile(text,'run-503.py','exec')
(HERE/'run-503.py').write_text(text,newline='\n')
(HERE/'runner-delta.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='run-502.py',tofile='run-503.py')),newline='\n')
(HERE/'prepare-result.json').write_text(json.dumps(dict(passed=True,original_runner_sha256=sha(OLD/'run-502.py'),
   candidate_runner_sha256=sha(HERE/'run-503.py'),metadata_sha256=sha(HERE/'metadata-proof.py'),
   source_candidate_delivery_sha256=sha(PREV/'delivery.json'),new_Image_built=False),indent=2)+'\n')
print(json.dumps(dict(prepared=True,runner_sha256=sha(HERE/'run-503.py'),metadata_sha256=sha(HERE/'metadata-proof.py'))))
