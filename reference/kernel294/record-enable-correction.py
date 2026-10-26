"""Record the independently pinned port-to-register proof and retain the failed first interpretation."""
from pathlib import Path
import hashlib,json,re,struct
ROOT=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel294')
p=ROOT/'protocol-contract-validation.json';old=json.loads(p.read_text());assert old['bhist']['enable']=='0x44 bit5'
(ROOT/'initial-protocol-contract-validation.json').write_bytes(p.read_bytes())
settings=(P/'reference-camxsettings.xml-private').read_text()
assert re.search(r'IFEOutputPortStatsBHIST\s*=\s*0x10000',settings) and re.search(r'IFEOutputPortStatsRS\s*=\s*0x1000',settings)
header=(P/'reference-camxispiqmodule.h-private').read_text();frag=header[header.index('struct IFEOutputPath'):];assert re.search(r'UINT32\s+path\s*;',frag[:350])
assert 'pStatsEnable->SKIN_BHIST_EN = pIFEOutputPathInfo[IFEOutputPortStatsBHIST].path;' in (P/'reference-camxtitan170ife.cpp-private').read_text()
binary=P.parent/'kernel281/camera.qcom.so-private';b=binary.read_bytes();assert hashlib.sha256(b).hexdigest()==old['hal_sha256']
off=struct.unpack_from('<Q',b,32)[0];size,count=struct.unpack_from('<HH',b,54)
def word(addr):
 for i in range(count):
  typ,flags,start,base,phys,length,*_=struct.unpack_from('<IIQQQQQQ',b,off+i*size)
  if typ==1 and base<=addr<base+length:return struct.unpack_from('<I',b,start+addr-base)[0]
 raise AssertionError(hex(addr))
for addr,value in {0x2a8ec8:0xb94042a7,0x2a8ecc:0x331c00e8,0x2a8ed4:0xb94032af,0x2a8ed8:0x331b01e8}.items():assert word(addr)==value
report=dict(stage=294,original_interpretation_wrong=True,first_capture_histogram_all_zero=True,
 bhist_port_index=16,bhist_path_byte_offset=64,bhist_enable_register='0x44',bhist_enable_bit=4,
 rs_port_index=12,rs_path_byte_offset=48,rs_enable_bit=5,
 independent_port_enumeration_and_u32_path_layout_verified=True,pinned_original_hal_instruction_words_verified=True,
 readonly_live_registers_confirm_initial_wrong_bit=True,no_mmio_writes_performed=True,
 kernel_fix_and_standard_api_retest_pending=True)
(ROOT/'enable-correction-validation.json').write_text(json.dumps(report,indent=2)+'\n')
old['bhist']['enable']='0x44 bit4';old['initial_wrong_enable']='0x44 bit5 (RS)';old['correction_evidence']='enable-correction-validation.json';p.write_text(json.dumps(old,indent=2)+'\n')
print(json.dumps(report,indent=2))
