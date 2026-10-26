from pathlib import Path
import runpy,os
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel118/ensure-build-volume.py'));runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
p='/home/cy122/pmos-samurai-kernel118/camera120/schema-venv/bin/python';os.execv(p,[p,str(r/'reference/kernel126/validate-camss-schema.py')])
