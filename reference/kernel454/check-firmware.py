"""Execute the actual candidate C parser against the privately converted tables."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
storage.mount.mounted_build()
P=Path('/mnt/e/edk2-samurai-out/kernel454')
firmware=P/'ov02a1b-1600x1200-private.bin'
receipt=json.loads((HERE/'firmware-validation.json').read_text())
assert receipt['passed'] and hashlib.sha256(firmware.read_bytes()).hexdigest()==receipt['firmware_sha256']
q=subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(HERE),str(HERE/'firmware-contract.c'),'-o',str(P/'firmware-contract')],capture_output=True)
(P/'firmware-c-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode
q=subprocess.run([str(P/'firmware-contract'),str(firmware)],capture_output=True)
(P/'firmware-c-run-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode
cases=json.loads(q.stdout)
r=dict(stage=454,actual_c_header_executed=True,asan_ubsan=True,firmware_sha256=receipt['firmware_sha256'],code_sha256=hashlib.sha256((HERE/'ov02a1b_firmware.h').read_bytes()).hexdigest(),cases=cases,ordered_private_table_views_equal=True,invalid_input_does_not_expose_partial_views=True,hardware_io_or_pm_or_driver_probe_tested=False,firmware_loader_not_integrated=True,no_phone_sdk=True,passed=True)
(HERE/'firmware-c-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
