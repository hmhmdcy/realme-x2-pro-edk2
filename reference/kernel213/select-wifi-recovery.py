from pathlib import Path
import json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213')
report=json.loads((here/'transport-recovery-validation.json').read_text());assert report['strict_original_key_wifi_responsive'] and report['current213_guard_verified'] and report['taint']==0
selection=private/'selected-transport-private.json';assert not selection.exists()
selection.write_text(json.dumps(dict(kind='wifi',current213_guard_verified=True,strict_original_key_verified=True,usb_large_transfer_truncated_and_then_small_ssh_timed_out=True),indent=2)+'\n')
print('Same-boot strict-key Wi-Fi selected for archive recovery; USB failure remains open.')
