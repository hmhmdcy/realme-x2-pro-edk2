from pathlib import Path
import json,struct
import host
HERE=Path(__file__).resolve().parent
hal=(host.PRIVATE.parent/'kernel316/hal-source/camera.qcom.so').read_bytes()
# Actual master DumpAEsyncData call; unlike the complete descriptors, this is
# an OEM branch-specific offset and is checked separately without applying it.
words={0x50323c:0x52868001,0x503240:0x52800022,0x503250:0x94000b32,0x503610:0x5285a001,0x503614:0x52800062,0x503620:0x94000a3e}
for address,word in words.items():assert struct.unpack_from('<I',hal,address)[0]==word
plan=dict(stage=326,plans=[dict(label='s5kgw1-ae-master',model='s5kgw1',address7=0x50,start=0x3400,read_bytes=36,address_bytes=2,data_bytes=1,operation='READ')],
 source_hal_stage=316,source_hal_sha256='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde',
 master_call={'offset_instruction':'0x50323c','role_instruction':'0x503240','call':'0x503250','callee':'0x505f18'},
 offset_from_legacy_named_branch=True,current_descriptor_range_ends=9984,extended_small_read_only=True,
 no_vendor_code_executed=True,no_values_applied=True,passed=True)
(HERE/'ae-read-plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('Pinned master reference offset0x3400; targeted36-byte read, outside normal descriptor segment; no writes.')
