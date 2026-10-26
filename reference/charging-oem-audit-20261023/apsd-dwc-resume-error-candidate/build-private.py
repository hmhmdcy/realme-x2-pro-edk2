"""Reuse the affected-object builder with a separate source view/O directory."""
from pathlib import Path
import hashlib

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'apsd-dwc-window-candidate-r2'
EXPECTED='aa01bb35397a9927bc98409f7a332df6486c6cdfedf4972a7030f7873cb78531'

def main():
    original=(BASE/'build-private.py').read_bytes()
    assert hashlib.sha256(original).hexdigest()==EXPECTED
    source=original.decode()
    replacements={
        "apsd-dwc-window-candidate-r2')":"apsd-dwc-resume-error-candidate')",
        "(HERE/'baseline.json')":"(BASE/'baseline.json')",
        "shutil.copy2(HERE/name,target)":"shutil.copy2(HERE/name if name=='core.c' else BASE/name,target)",
        "['modules_prepare','drivers/usb/dwc3/gadget.o']":"['modules_prepare','drivers/usb/dwc3/core.o']",
        "sources={n:sha(HERE/n) for n in ['core.h','core.c','gadget.c']}":
        "sources={n:sha(HERE/n if n=='core.c' else BASE/n) for n in ['core.h','core.c','gadget.c']}",
    }
    for old,new in replacements.items():
        assert source.count(old)==1,old
        source=source.replace(old,new)
    ns={'__file__':str(HERE/'build-private.py'),'__name__':'__main__','BASE':BASE}
    exec(compile(source,'<fixed-private-dwc-object-builder>','exec'),ns)

if __name__=='__main__':main()
