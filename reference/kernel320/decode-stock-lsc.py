"""Follow the target HAL's extra byte after every 51 packed40 points."""
from pathlib import Path
import hashlib,json,math,statistics,struct
HERE=Path(__file__).resolve().parent;ROOT=Path('/mnt/e/edk2-samurai-out');P=ROOT/'kernel320';P.mkdir(mode=0o700,exist_ok=True)
raw=(ROOT/'kernel299/imx319-eeprom-read1-private.bin').read_bytes()
unit=[[] for _ in range(4)]
for point in range(221):
 at=208+5*point+point//51
 low=raw[at:at+4];high=raw[at+4]
 for c in range(4):unit[c].append(low[c]+((high>>(6-2*c))&3)*256)
zero=sum(v==0 for channel in unit for v in channel)
def roughness(v):
 pairs=[(v[y*17+x],v[y*17+x+1]) for y in range(13) for x in range(16)]
 pairs += [(v[y*17+x],v[(y+1)*17+x]) for y in range(12) for x in range(17)]
 return statistics.mean([(a-b)**2 for a,b in pairs])/(2*statistics.pvariance(v))
footer=[]
for group in range(4):
 start=208+group*256;data=raw[start:start+255];value=raw[start+255]
 xor=0
 for v in data:xor^=v
 footer.append(dict(group=group,offset=start+255,value=value,sum_mod256=sum(data)%256,sum_mod255_plus1=sum(data)%255+1,xor=xor))
factory=json.loads((ROOT/'kernel317/factory-lsc-decoded-private.json').read_text())['factory']
candidate=[]
for root in factory:
 golden=root['golden'][0]['gains'];channels=['r','gr','gb','b']
 ratios={c:[g/u if u else None for g,u in zip(golden[c],unit[i])] for i,c in enumerate(channels)}
 candidate.append(dict(uid=root['uid'],golden_over_unit=ratios))
(P/'stock-unit-lsc-private.json').write_text(json.dumps(dict(channels=unit,footers=footer,candidate_factors=candidate,applied=False),indent=2)+'\n')
report=dict(stage=320,stock_hal_sha256=hashlib.sha256((ROOT/'kernel316/hal-source/camera.qcom.so').read_bytes()).hexdigest(),
 stock_instruction_evidence={'loop':'0x4fe070..0x4fe130','ordinary_increment':'0x4fe00c..0x4fe06c','group_test':'0x4fe134..0x4fe154','extra_increment':'0x4fe158..0x4fe1a4'},
 address_formula='208 + 5 * point + floor(point / 51)',points=221,channel_order=['R','GR','GB','B'],
 old_layout_zero_samples=4,new_layout_zero_samples=zero,new_channel_neighbor_roughness=[roughness(v) for v in unit],
 footer_sum_mod256_matches=sum(f['value']==f['sum_mod256'] for f in footer),
 footer_sum_mod255_plus1_matches=sum(f['value']==f['sum_mod255_plus1'] for f in footer),
 footer_xor_matches=sum(f['value']==f['xor'] for f in footer),footer_groups=4,
 factory_checksum_verified=False,individual_values_applied=False,phone_changed=False)
(HERE/'stock-lsc-layout-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
