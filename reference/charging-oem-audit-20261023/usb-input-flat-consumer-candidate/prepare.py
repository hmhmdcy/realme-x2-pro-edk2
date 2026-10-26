"""Derive one lifetime-only USB change from exact R8; no runtime action."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]/'charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
expected={'samurai-usb-input.c':'b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098',
          'samurai-usb-input-decode.h':'a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd'}
raws={name:(BASE/name).read_bytes() for name in expected}
for name,digest in expected.items():assert sha(raws[name])==digest,name
old=raws['samurai-usb-input.c'].decode()
anchor='\tof_node_put(node);\n}\n\nstatic int samurai_usb_probe'
assert old.count(anchor)==1
addition='''\tof_node_put(node);
\tif (native_retained)
\t\treturn;

\t/* The combined Qualcomm driver owns the same native supply reference
\t * on a flat controller. Never retain for an unavailable or unrelated node.
\t * Keep the established legacy-path selection above unchanged.
\t */
\tnode = of_find_node_by_path("/soc@0/usb@a600000");
\tif (node && of_device_is_available(node) &&
\t    of_device_is_compatible(node, "qcom,snps-dwc3") &&
\t    !of_property_read_string(node, "usb-psy-name", &name) &&
\t    !strcmp(name, "samurai-usb-input")) {
\t\t__module_get(THIS_MODULE);
\t\tnative_retained = true;
\t\tdev_info(dev, "native DWC3 supply retained until next boot\\n");
\t}
\tof_node_put(node);
}

static int samurai_usb_probe'''
candidate=old.replace(anchor,addition)
(HERE/'samurai-usb-input.c').write_text(candidate,encoding='utf-8',newline='\n')
(HERE/'samurai-usb-input-decode.h').write_bytes(raws['samurai-usb-input-decode.h'])
(HERE/'flat-consumer.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),candidate.splitlines(True),
    fromfile='r8/samurai-usb-input.c',tofile='flat-consumer/samurai-usb-input.c')),encoding='utf-8',newline='\n')
start=old.index('static void samurai_usb_retain_for_native_consumer')
end=old.index('\nstatic int samurai_usb_probe',start)
actual_start=candidate.index('static void samurai_usb_retain_for_native_consumer')
actual_end=candidate.index('\nstatic int samurai_usb_probe',actual_start)
before,after=old[start:end],candidate[actual_start:actual_end]
assert candidate[:actual_start]==old[:start] and candidate[actual_end:]==old[end:]
assert after[:after.index('\tif (native_retained)')]==before[:before.rindex('}')]
(HERE/'actual-retain.inc').write_text(after,encoding='utf-8',newline='\n')
result=dict(passed=True,baseline={name:dict(path=str((BASE/name).resolve()),sha256=digest) for name,digest in expected.items()},
    candidate_source_sha256=sha((HERE/'samurai-usb-input.c').read_bytes()),decoder_sha256=sha((HERE/'samurai-usb-input-decode.h').read_bytes()),
    actual_function_sha256=sha((HERE/'actual-retain.inc').read_bytes()),only_changed_function='samurai_usb_retain_for_native_consumer',
    legacy_prefix_byte_identical=True,all_other_source_bytes_identical=True,IRQ_or_budget_or_PMIC_or_poll_changed=False,
    flat_node='/soc@0/usb@a600000',flat_required_compatible='qcom,snps-dwc3',flat_required_supply='samurai-usb-input',
    flat_requires_available=True,legacy_path='/soc@0/usb@a6f8800/usb@a600000',device_accessed=False)
(HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
