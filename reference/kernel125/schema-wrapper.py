import os,runpy
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
p='/home/cy122/pmos-samurai-kernel118/camera120/schema-venv/bin/python'
os.execv(p,[p,'/mnt/e/RealmeX2Pro edk2/reference/kernel125/validate-camss-schema.py'])
