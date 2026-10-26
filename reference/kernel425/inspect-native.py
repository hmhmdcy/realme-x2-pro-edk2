from pathlib import Path
import importlib.util,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);storage.mounted_build()
hal=P.parent/'kernel281/camera.qcom.so-private'
for name,a,b in [('ltm-dc',0x1556a0,0x1557c8),('set-config-io',0x2e4b88,0x2e4f00),('create-striping',0x144348,0x1448f0),('image-plane-size',0x4535d8,0x453a00)]:
 data=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(a),'--stop-address='+hex(b),str(hal)])
 (P/(name+'-private.asm')).write_bytes(data)
print('Retained native coarse, config, striping-create and format helpers saved privately.')
