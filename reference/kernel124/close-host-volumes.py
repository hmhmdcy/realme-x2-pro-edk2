from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2')
code=(root/'reference/kernel122/close-host-volumes.py').read_text()
code=code.replace("out=Path('/mnt/e/edk2-samurai-out/kernel122')","out=Path('/mnt/e/edk2-samurai-out/kernel124')")
code=code.replace('reference/kernel122/host-volume-validation.json','reference/kernel124/host-volume-validation.json')
exec(compile(code,'close-new-e-volumes-124','exec'),{})
