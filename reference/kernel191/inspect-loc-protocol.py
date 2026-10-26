from pathlib import Path
import host
code=b'''from pathlib import Path
import json,re
p=Path('/var/lib/samurai/k190-mm-sdk/usr/include/libqmi-glib/qmi-loc.h')
text=p.read_text()
names=sorted(set(re.findall(r'qmi_indication_loc_inject_(?:xtra_data|predicted_orbits_data|utc_time|position)_output_get_[a-z_]+',text)))
print(json.dumps(dict(installed_sdk_getters=names)))
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
(Path(__file__).resolve().parent/'loc-protocol-api-validation.json').write_bytes(p.stdout)
host.download('/var/lib/samurai/k190-mm-sdk/usr/include/libqmi-glib/qmi-loc.h',host.PRIVATE/'qmi-loc-sdk-private.h')
