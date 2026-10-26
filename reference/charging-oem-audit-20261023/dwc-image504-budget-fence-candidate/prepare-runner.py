"""Generate/check the Image504 plan only; never enters storage or builds."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
METHOD=REF/'charging-session-20261023/dwc-image503-start-recovery-candidate'
FROZEN=HERE.parent/'dwc-vbus-budget-fence-candidate'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(METHOD/'delivery.json')=='e4e059334aab56acd8dde25348ba19aec2af9790b93fb632295e5b63a4ef9374'
method=json.loads((METHOD/'delivery.json').read_bytes())
for name,pin in method['files'].items():assert sha(METHOD/name)==pin,name
assert sha(METHOD/'run-503.py')=='760223a1092bb41f4f7b000143a1510fb9ea4fdb85efb73e35bba2304a64e340'
assert sha(FROZEN/'delivery.json')=='8d7a963a3aef17a16ef5e8ec19d96b31de4f066b261e315d28727c6d0b1e16aa'
assert sha(FROZEN/'object-build/delivery.json')=='8b25d5b27fc9d099379ab6efeb58e2a5e915c3283f650967dad3e21528151a82'
original=(METHOD/'run-503.py').read_text()
text=original
def replace(old,new):
    global text
    assert text.count(old)==1,(old,text.count(old))
    text=text.replace(old,new,1)
replace('"""Private consistent DWC Image503 from passed 502; no boot packaging/device."""',
        '"""Private Image504 software budget fence from original 502; no boot packaging/device."""')
replace("OUT=Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01')",
        "OUT=Path('/home/cy122/charging-management-20261023/dwc-image504-budget-fence-01')")
start=text.index("FROZEN=HERE.parent/'dwc-device-start-recovery-candidate'")
end=text.index('METADATA_SHA=',start)
sources={'drivers/usb/dwc3/core.c':'6c8e5e33cc890afcfafbcbe2d339164a590edc0024fe41d3178f90f410790e20',
         'drivers/usb/dwc3/core.h':'e2a21d2edaf0b48b91e77dc257287516e009859981c0370f747afd9898fbdb79',
         'drivers/usb/dwc3/gadget.c':'228caf6f2dd3bfcec12fb1ec22b1f72eb1d5b02520d7917393a094a4ffab6fbf'}
base_sources={'core.c':'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf',
              'core.h':'525c1d5d8d0e501f4a92ddd6232961542b5c04521f29a50b8acf9ee86c41373c',
              'gadget.c':'9eec86e42945a786447e6a6548a25b495e29a01bed8e8fbfc13e02903e1ff0c5'}
text=text[:start]+"FROZEN=HERE.parent/'dwc-vbus-budget-fence-candidate'\nDWC_SOURCES="+repr(sources)+"\nBASE_DWC_SOURCES="+repr(base_sources)+"\n"+text[end:]
start=text.index('def check_local():')
end=text.index('\ndef prove_additional(',start)
pins={
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/delivery.json':'4e27a8da005b3e5b41799f63a9a3b3e4de1b22f6d60f8a1172c2c28cd8163e21',
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/build-result.json':'feb6fd2e8ef8ca380f48a6f8f88b131646a874fa1d8660c3bde83a38ec8940e6',
 'charging-ui-audit-20261023/gauge-image502-notify-candidate/abi-reuse-result.json':'b097ee9314bd7b913fd2ec08a462b6e04d8ed68c635a168080f4e035b149b230',
 'charging-oem-audit-20261023/dwc-vbus-budget-fence-candidate/delivery.json':'8d7a963a3aef17a16ef5e8ec19d96b31de4f066b261e315d28727c6d0b1e16aa',
 'charging-oem-audit-20261023/dwc-vbus-budget-fence-candidate/object-build/delivery.json':'8b25d5b27fc9d099379ab6efeb58e2a5e915c3283f650967dad3e21528151a82',
 'charging-session-20261023/dwc-start-recovery-image-integration-plan/dependency-result.json':'bec66bdf580ce4541f19b60fb5f4865649f48376ba5bbfcc159424455fef8b46',
 'charging-session-20261023/dwc-image503-start-recovery-candidate/delivery.json':sha(METHOD/'delivery.json'),
 'charging-session-20261023/dwc-image503-start-recovery-candidate/run-503.py':sha(METHOD/'run-503.py'),
}
text=text[:start]+'''def check_local():
    assert not sys.flags.optimize, 'Non-optimized interpreter required'
    pins = '''+repr(pins)+'''
    for name,digest in pins.items(): assert sha(REF/name)==digest,name
    for leaf in [PREVIOUS,FROZEN]:
        delivery=json.loads((leaf/'delivery.json').read_bytes())
        assert delivery['passed']
        for name,row in delivery['files'].items():
            digest=row['sha256'] if isinstance(row,dict) else row
            assert sha(leaf/name)==digest,name
    build_delivery=json.loads((FROZEN/'object-build/delivery.json').read_bytes())
    assert build_delivery['passed'] and build_delivery['all_eight_core_h_consumers_compiled_W1_Werror']
    for name,row in build_delivery['files'].items(): assert sha(FROZEN/'object-build'/name)==row['sha256'],name
    for name,digest in DWC_SOURCES.items(): assert sha(FROZEN/Path(name).name)==digest,name
    assert sha(HERE/'metadata-proof.py')==METADATA_SHA
'''+text[end:]
replace("env.update(KBUILD_BUILD_VERSION='503',", "env.update(KBUILD_BUILD_VERSION='504',")
replace("assert '#503 SMP PREEMPT '", "assert '#504 SMP PREEMPT '")
replace("'KBUILD_BUILD_VERSION':'503'", "'KBUILD_BUILD_VERSION':'504'")
replace("str(HERE/'run-503.py')", "str(HERE/'run-504.py')")
replace("assert sys.argv[1:]==['--execute-503'],'Explicit --execute-503 required'",
        "assert sys.argv[1:]==['--execute-504'],'Explicit --execute-504 required'")
replace("scope=json.loads((HERE.parent/'dwc-start-recovery-image-integration-plan/dependency-result.json').read_bytes())",
        "scope=json.loads((REF/'charging-session-20261023/dwc-start-recovery-image-integration-plan/dependency-result.json').read_bytes())")
replace("    assert sha(BASE/'source354/drivers/usb/dwc3/core.h')=='525c1d5d8d0e501f4a92ddd6232961542b5c04521f29a50b8acf9ee86c41373c'",
        "    for name,digest in BASE_DWC_SOURCES.items():\n        assert sha(BASE/'source354/drivers/usb/dwc3'/name)==digest,name")
# Report the actual unchanged count; only the same eight targets/metadata may differ.
text=text.replace("len(leaves)-9", "sum(after[n]==original[n] for n in leaves)")
metadata=(METHOD/'metadata-proof.py').read_text()
assert metadata.count("NEW_ID=b'#503 ")==1
metadata=metadata.replace("NEW_ID=b'#503 ","NEW_ID=b'#504 ")
(HERE/'metadata-proof.py').write_text(metadata,encoding='utf-8',newline='\n')
replace("METADATA_SHA='0b029754c347f93e18f285bc508c5f2625684498e5b78de453bb71dbe96ac7c9'",
        'METADATA_SHA='+repr(sha(HERE/'metadata-proof.py')))
compile(text,'run-504.py','exec')
assert "BASE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')" in text
assert 'dwc-device-start-recovery-candidate' not in text and 'dwc-pm-error-unwind-candidate' not in text
assert text.count("run('B-dwc-eight-objects',argv+DWC_TARGETS)")==1 and text.count("run('B-image',argv+['Image'])")==1
(HERE/'run-504.py').write_text(text,encoding='utf-8',newline='\n')
(HERE/'runner-delta.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),
    fromfile='frozen/run-503.py',tofile='run-504.py')),encoding='utf-8',newline='\n')
result=dict(schema='samurai-image504-budget-fence-prepared-plan-v1',passed=True,
    method_delivery_sha256=sha(METHOD/'delivery.json'),method_runner_sha256=sha(METHOD/'run-503.py'),
    method_prepare_sha256=sha(METHOD/'prepare-runner.py'),candidate_runner_sha256=sha(HERE/'run-504.py'),
    metadata_sha256=sha(HERE/'metadata-proof.py'),actual_base='gauge-image502-notify-01',
    actual_base_DWC_sources=base_sources,new_DWC_sources=sources,identity='#504',
    old_initramfs_gauge_notify_and_default_B_mode_preserved=True,default_mode='check-local',
    only_Kbuild_eight_then_Image_planned=True,raw_GCC_objects_not_imported=True,
    new_Image_built=False,storage_or_device_invoked=False)
(HERE/'prepare-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(prepared=True,runner_sha256=sha(HERE/'run-504.py'),metadata_sha256=sha(HERE/'metadata-proof.py'))))
