from pathlib import Path
from urllib.request import Request,urlopen
import base64,hashlib,json

here=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel208/receiver-sources')
url='https://android.googlesource.com/platform/hardware/qcom/gps/+/android-4.2.2_r1/loc_api/loc_api_v02/location_service_v02.h?format=TEXT'
with urlopen(Request(url,headers={'User-Agent':'samurai-location-contract-review'}),timeout=35) as response:data=base64.b64decode(response.read(4_000_000),validate=True)
(out/'location_service_v02.h').write_bytes(data)
report=dict(stage=208,official_historical_idl_url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),use='session_and_NMEA_delivery_contract_only_not_SM8150_feature_inventory')
(here/'loc-idl-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
