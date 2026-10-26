"""Extract newly located stock blocks from the existing private EEPROM sample."""
from pathlib import Path
import hashlib,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
hal=(P/'hal-source/camera.qcom.so').read_bytes()
assert hashlib.sha256(hal).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
# Exact branch/callee instruction words used as the provenance of these offsets.
instructions={0x5032c0:0x52830ec1,0x5032c4:0x5284bce2,0x504690:0x38686809,
 0x504694:0x7100053f,0x5046c8:0x5281ae37,0x504bb0:0x3dc02ea0,
 0x504bb8:0x394302a9,0x5033b8:0x5285a001,0x505fac:0x52800496}
for address,word in instructions.items():assert struct.unpack_from('<I',hal,address)[0]==word
sample=(P.parent/'kernel299/imx319-eeprom-read1-private.bin').read_bytes()
assert len(sample)==12287
out=P/'unit-calibration-blocks';out.mkdir(exist_ok=True)
blocks={'serial':(0xb0,17),'distortion':(0x1876,3441),'ae_sync_wide':(0x2d00,36)}
private={}
for name,(start,length) in blocks.items():
 data=sample[start:start+length];assert len(data)==length
 (out/(name+'.bin')).write_bytes(data)
 private[name]={'start':start,'length':length,'sha256':hashlib.sha256(data).hexdigest(),
  'nontrivial':bool(set(data)-{0,255})}
private['distortion']['oem_flag']=sample[0x25e7]
private['ae_sync_wide']['oem_sentinel_guard']=sample[0x2d00]!=255
(out/'manifest-private.json').write_text(json.dumps(private,indent=2)+'\n')
report={'stage':316,'source':'exact stock camera.qcom.so','source_sha256':hashlib.sha256(hal).hexdigest(),
 'source_readonly_unmounted':True,'oem_code_executed':False,'existing_sample_stage':299,
 'sensor_eeprom_name':'fx319aa_imx319','role_argument':2,
 'serial':{'offset':0xb0,'bytes':17,'nontrivial':private['serial']['nontrivial'],'data_and_hash_private':True},
 'distortion':{'offset':0x1876,'bytes':3441,'flag_offset':0x25e7,'flag_valid':sample[0x25e7]==1,'semantics':'DumpDistortionData tests byte==1 before copying3441bytes; not a CRC check','intrinsics_decoded':False},
 'ae_sync':{'offset':0x2d00,'bytes':36,'initial_sentinel_guard_passed':sample[0x2d00]!=255,'semantics':'DumpAEsyncData initially rejects firstbyte0xff; CalculateAESync also checks numerical validity','field_layout_decoded':False},
 'factory_wb_lsc_checksum_verified':False,'individual_calibration_applied':False,'goal_complete':False}
(HERE/'oem-calibration-block-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
