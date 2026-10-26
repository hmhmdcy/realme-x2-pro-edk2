from pathlib import Path
import hashlib,json,re,struct
import host
ROOT=Path(__file__).resolve().parent
b=Path('/mnt/e/edk2-samurai-out/kernel281/camera.qcom.so-private').read_bytes();assert hashlib.sha256(b).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
offset=struct.unpack_from('<Q',b,32)[0];size,count=struct.unpack_from('<HH',b,54);loads=[]
for i in range(count):
 kind,flags,start,address,phys,length,*_=struct.unpack_from('<IIQQQQQQ',b,offset+i*size)
 if kind==1:loads.append((address,start,length))
def read(address,size):
 for base,start,length in loads:
  if base<=address and address+size<=base+length:return b[start+address-base:start+address-base+size]
 raise AssertionError(hex(address))
instructions={0x3123e8:0x52817c81,0x3123ec:0x52800042,0x312168:0x1208716f,0x312180:0x331c0083,
 0x3122d4:0x12003165,0x3122e0:0x12002da6,0x3122e4:0x33103525,0x3122ec:0x33103146,
 0x2a9450:0x910fb269,0x2a9454:0xf90027e9,0x2a94c0:0x910fc26b,0x2a94c4:0xf90023eb,
 0x2a99a4:0xf94027e3,0x2a99ac:0x52800881,0x2a99bc:0xf94023e3,0x2a99c4:0x52815581,
 0x2a8ec8:0xb94042a7,0x2a8ecc:0x331c00e8,0x2a8ed4:0xb94032af,0x2a8ed8:0x331b01e8,0x312dc0:0x5280d601,0x312dc4:0x52800062}
for addr,value in instructions.items():assert struct.unpack('<I',read(addr,4))[0]==value,hex(addr)
bus=(host.PRIVATE/'oem-cam_vfe_bus_ver2.c-private').read_text();assert 'case CAM_VFE_BUS_VER2_VFE_OUT_STATS_BHIST:' in bus
frag=bus[bus.index('case CAM_VFE_BUS_VER2_VFE_OUT_STATS_BHIST:',bus.index('cam_vfe_bus_get_wm_idx')):]
assert 'wm_idx = 16;' in frag[:400]
assert 'rsrc_data->index >= 11 && rsrc_data->index < 20' in bus and 'rsrc_data->en_cfg = 0x3;' in bus
reference=(host.PRIVATE/'reference-camxifebhiststats14.h-private').read_text();assert re.search(r'ChannelSelectY\s*=\s*0x0',reference) and re.search(r'BHistBinsPerChannel\s*=\s*1024',reference)
report=dict(stage=294,hal_sha256=hashlib.sha256(b).hexdigest(),checked_instruction_addresses=[hex(a) for a in instructions],
 bhist=dict(region_registers=['0xbe4','0xbe8'],offset_h_bits='12:0',offset_v_bits='29:16',count_h_bits='11:0',count_v_bits='28:16',
  offsets_in_pixels=True,region_unit_pixels=[2,2],minimum_region_pixels=[4,2],channel_y=0,channel_bits='23:21',uniform_bit=4,stats_config='0xaac',enable='0x44 bit4',bins=1024,bin_bytes=4,
  histogram_input='14-bit pipeline, uniform right-shift to 10-bit bins, pre-gamma demosaic tap',stats_dma_client=16,stats_packet_mode=3,stats_stride=1),
 bls=dict(register_start='0x6b0',register_count=3,implementation_and_tuning_not_yet_added=True),
 no_oem_binary_execution=True,no_oem_implementation_copied=True,not_hardware_validated=True)
(ROOT/'protocol-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
