from pathlib import Path
import json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');fresh=json.loads((private/'fresh-working-endpoint-private.json').read_text());proof=fresh['proof'];assert fresh['kind']=='usb' and proof['same_213_guard'] and proof['expected_model'] and proof['taint']==0
target=private/'usb-ipv6-candidates-private.json';assert not target.exists();target.write_text(json.dumps(dict(IPAddress=fresh['IPAddress'],State='freshly authenticated'),indent=2)+'\n')
old=json.loads((private.parent/'kernel213/usb-ipv6-candidates-private.json').read_text(encoding='utf-8-sig'))
report=dict(stage=214,fresh_strict_usb_endpoint_selected=True,same_213_boot_and_model_verified=True,taint=0,scoped_endpoint_changed_from_saved213=fresh['IPAddress']!=old['IPAddress'],no_device_configuration_or_partition_change=True)
(here/'transport-selection-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
