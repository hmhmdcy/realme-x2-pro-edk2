"""Bind the actual completed offline carrier; no deployment or phone identity."""
from pathlib import Path
import importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cohort',HERE/'cohort.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
receipt=HERE.parent.parent/'charging-oem-audit-20261023/image504-budget-logdump-candidate/logdump-result.json'
assert c.file_sha(receipt)=='f1cdce8c66bf3a1c670a64ee1306f5af56efc79ad142f950364b0c311bad938d'
r=json.loads(receipt.read_bytes())
image={'sha256':'f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4','bytes':59243008}
path=Path('E:/edk2-samurai-out/charging-management-20261023/image504-budget-logdump-private-01/logdump-image504-private.img')
data=dict(receipt=dict(path=str(receipt),sha256=c.file_sha(receipt),bytes=receipt.stat().st_size),
    logdump=dict(path=str(path),sha256='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83',bytes=67108864),
    Image504_sha256=image['sha256'])
c.validate_carrier(r,data,image);c.pinned(data['logdump'])
target=HERE/'carrier-input.json';assert not target.exists()
target.write_bytes(c.encode(data));print(json.dumps(dict(passed=True,actual_completed_carrier_bound=True,carrier_input_sha256=c.file_sha(target),deployed=False)))
