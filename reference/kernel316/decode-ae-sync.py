"""Decode only the fields whose byte arithmetic is explicit in the stock HAL."""
from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
hal=(P/'hal-source/camera.qcom.so').read_bytes()
# Wide path reads25bytes and uses the same field offsets as the master's36byte path.
expected={0x505514:0x52800322,0x50552c:0x394037e7,0x505534:0x394017e1,
 0x50553c:0x394013e5,0x505544:0x394033ea,0x50554c:0x394027ee,
 0x505558:0x394023f0,0x50555c:0x39403bf1,0x505564:0x39401bef,
 0x50556c:0x39402be3,0x505574:0x39403fe5,0x50557c:0x394043e1,
 0x505aec:0x1e211962,0x505af4:0x1e251886}
for address,word in expected.items():assert struct.unpack_from('<I',hal,address)[0]==word
raw=(P/'unit-calibration-blocks/ae_sync_wide.bin').read_bytes()
fields={'mean_luma':(4,3),'gain_times100':(8,3),'exposure_times1000':(12,5)}
decoded={};valid=True
for name,(start,width) in fields.items():
 data=raw[start:start+width]
 if not data.isdigit():valid=False;decoded[name]=None;continue
 # Stock ISA uses weighted ASCII bytes minus48*(111 or11111).
 arithmetic=sum(value*10**(width-i-1) for i,value in enumerate(data))-48*sum(10**i for i in range(width))
 assert arithmetic==int(data)
 decoded[name]=arithmetic
decoded['gain']=decoded['gain_times100']/100 if decoded['gain_times100'] is not None else None
decoded['exposure_oem_units']=abs(decoded['exposure_times1000'])/1000 if decoded['exposure_times1000'] is not None else None
valid &= all(value is not None and value>0 for value in decoded.values())
(P/'unit-calibration-blocks/ae-sync-decoded-private.json').write_text(json.dumps(dict(fields=decoded,valid=valid,source_function='CalculateAESync',applied=False),indent=2)+'\n')
report=dict(stage=316,sensor='imx319',source_function_virtual_address='0x504f30',
 fields={k:{'offset':v[0],'ascii_digits':v[1]} for k,v in fields.items()},
 stock_gain_divisor=100,stock_exposure_divisor=1000,exposure_physical_unit_not_verified=True,
 unit_fields_ascii_and_nonzero=valid,master_reference_missing=True,
 stock_luma_ratio='slave_mean_luma/master_mean_luma; gains and exposure references stored separately',
 values_private=True,factory_checksum_verified=False,calibration_applied=False)
(HERE/'ae-sync-decode-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
