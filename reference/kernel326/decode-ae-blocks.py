"""Decode the OEM reference records without guessing their physical time unit."""
from pathlib import Path
import json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'transfer-ae1-validation.json').read_text())['passed']
master=(P/'reads-ae1/s5kgw1-ae-master-read1-private.bin').read_bytes()
wide=(P.parent/'kernel299/imx319-eeprom-read1-private.bin').read_bytes()[0x2d00:0x2d00+36]
tele=(P/'reads-r2/s5k3m5-read1-private.bin').read_bytes()[0x2d00:0x2d00+36]
assert len(master)==len(wide)==len(tele)==36
fields={'mean_luma':(4,3),'gain_times100':(8,3),'exposure_times1000':(12,5)}
def decode(raw):
 out={};valid=raw[0]!=255
 for name,(start,width) in fields.items():
  digits=raw[start:start+width]
  if not digits.isdigit():out[name]=None;valid=False;continue
  value=int(digits);assert value==sum((byte-48)*10**(width-i-1) for i,byte in enumerate(digits));out[name]=value
 valid &= all(v is not None and v>0 for v in out.values())
 if valid:out.update(gain=out['gain_times100']/100,exposure_oem_units=out['exposure_times1000']/1000)
 return dict(fields=out,sentinel_passed=raw[0]!=255,ascii_fields_positive=valid)
decoded={name:decode(raw) for name,raw in [('master',master),('wide',wide),('tele',tele)]}
pair=decoded['master']['ascii_fields_positive'] and decoded['wide']['ascii_fields_positive']
if pair:
 m=decoded['master']['fields'];w=decoded['wide']['fields']
 ratio=w['mean_luma']/m['mean_luma']
 # The HAL stores this luma ratio and both exposure/gain references. The
 # normalized response below is a separate dimensional inference, not a
 # claim that the OEM code uses this formula or that a time unit is known.
 response=ratio*(m['gain']*m['exposure_oem_units'])/(w['gain']*w['exposure_oem_units'])
 assert math.isfinite(response) and response>0
 decoded['wide_master_pair']=dict(stock_luma_ratio=ratio,derived_response_normalization=response,derived_ev_offset=math.log2(response),derived_quantity_not_oem_formula=True)
(P/'decoded-ae-reference-private.json').write_text(json.dumps(decoded,indent=2)+'\n')
report=dict(stage=326,master_offset='0x3400',master_bytes=36,master_source_call='0x503250 -> 0x505f18',slave_offset='0x2d00',
 fields={k:dict(offset=v[0],ascii_digits=v[1]) for k,v in fields.items()},records={k:{n:r[n] for n in ['sentinel_passed','ascii_fields_positive']} for k,r in decoded.items() if k!='wide_master_pair'},
 master_reference_recovered=pair,stock_gain_divisor=100,stock_exposure_divisor=1000,exposure_physical_unit_not_verified=True,
 stock_luma_ratio='slave_mean_luma/master_mean_luma; gains and exposure references stored separately',
 tele_common_field_layout_is_candidate=True,values_and_derived_coefficients_private=True,factory_checksum_verified=False,
 calibration_applied=False,hardware_frame_synchronization_verified=False,passed=True)
(HERE/'ae-reference-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
