"""Derive only one private gadget.o builder from the passed core.o builder."""
from pathlib import Path
import ast
import hashlib
import json
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'dwc-pm-error-unwind-candidate/build-object.py'
text=BASE.read_text()
original=hashlib.sha256(BASE.read_bytes()).hexdigest()


def replace(old,new):
    global text
    assert text.count(old)==1,old
    text=text.replace(old,new)


replace('One private core.o','One private gadget.o')
replace("OUT = Path('/home/cy122/charging-management-20261023/dwc-pm-susphy-object-01')",
        "OUT = Path('/home/cy122/charging-management-20261023/dwc-suspend-halt-object-01')")
replace("tests['summary']['cases'] == 24","tests['summary']['cases'] == 13")
replace("expected = {'core.c':source['original_core_sha256'],\n                'core.h':source['Image503_core_h_sha256'],\n                'gadget.c':source['Image503_gadget_sha256']}",
        "expected = {'core.c':'bd8a8aabf199952717926b8ee79562e283ed9cd6a1ee485d22cd52167ad7ffcf',\n"
        "                'core.h':source['inputs']['core.h'],\n                'gadget.c':source['inputs']['gadget.c']}")
replace("'storage284_dwc_pm_object'","'storage284_dwc_halt_object'")
text=text.replace('drivers/usb/dwc3/.core.o.cmd','drivers/usb/dwc3/.gadget.o.cmd')
text=text.replace('drivers/usb/dwc3/core.o','drivers/usb/dwc3/gadget.o')
replace("candidate = view/'drivers/usb/dwc3/core.c'\n    candidate.unlink()  # Only the new, private symlink, never the source target.\n    shutil.copy2(HERE/'core.c', candidate)\n    assert not candidate.is_symlink() and candidate.stat().st_nlink == 1\n    assert sha(candidate) == source['candidate_core_sha256']",
        "candidate = view/'drivers/usb/dwc3/gadget.c'\n"
        "    for name, path in {'gadget.c':HERE/'gadget.c',\n"
        "                       'core.c':HERE.parent/'dwc-pm-error-unwind-candidate/core.c'}.items():\n"
        "        target = view/'drivers/usb/dwc3'/name\n"
        "        target.unlink()  # Only a new private symlink, never its source target.\n"
        "        shutil.copy2(path, target)\n"
        "        assert not target.is_symlink() and target.stat().st_nlink == 1\n"
        "    assert sha(candidate) == source['candidate_gadget_sha256']\n"
        "    assert sha(view/'drivers/usb/dwc3/core.c') == source['inputs']['core.c']")
replace("raw.count('/mnt/samurai-full282/source354/drivers/usb/dwc3/core.c')",
        "raw.count('/mnt/samurai-full282/source354/drivers/usb/dwc3/gadget.c')")
replace("assert source_pins == dict(expected, **{'core.c':source['candidate_core_sha256']})",
        "assert source_pins == dict(source['inputs'], **{'gadget.c':source['candidate_gadget_sha256']})")
replace("['build-object.py','test-result.json','core.c']","['build-object.py','prepare-build.py','test-result.json','gadget.c']")
ast.parse(text)
assert not (HERE/'build-object.py').exists(),'No replay of a prepared/used builder'
(HERE/'build-object.py').write_text(text,newline='\n')
(HERE/'build-source-reuse.json').write_text(json.dumps(dict(passed=True,
 original_builder_sha256=original,candidate_builder_sha256=hashlib.sha256(text.encode()).hexdigest(),
 same_single_child_wait_lifecycle=True,only_target_source_and_receipt_adaptation=True,
 no_build_started=True),indent=2)+'\n')
print(json.dumps(dict(prepared=True,builder_sha256=hashlib.sha256(text.encode()).hexdigest())))
