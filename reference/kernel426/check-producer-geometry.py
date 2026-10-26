"""Recover prerequisite target crop/depth/packing controls, without pixel DMA."""
from pathlib import Path
import importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build();n=module('ds426',HERE/'ds4-model.py');m=n.Machine()
index=json.loads((P.parent/'kernel333/sunny_s5kgw1-index-private.json').read_text());raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
root=next(r for r in json.loads((P/'sunny_s5kgw1-ds4-reserves-private.json').read_text()) if r['tag']=='ds4to1v10_ife_full_dc4')
def blob(uid):
 e=index['entries'][str(uid)];return raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
data=blob(root['uid']);revision_uid=struct.unpack_from('<Q',data,32)[0];parsed,_=m.parse(root['tag'],root['uid'],data,revision_uid,blob(revision_uid))
rows=[]
for width,height in [(128,128),(640,480),(650,480),(1920,1080),(4096,3072)]:
 registers,enable,obj=m.execute(parsed,width,height);assert enable==0x1400
 crop,rounding,packing,combined=m.producer_crops_and_round(width,height)
 assert crop==[(0xd84,struct.pack('<2I',height-1,width-1)),(0xda4,struct.pack('<2I',height//2-1,width//2-1))]
 assert rounding==[(0xd98,struct.pack('<2I',1023<<20,6)),(0xdb8,struct.pack('<2I',1023<<20,7))]
 assert packing==[(0xd6c,struct.pack('<I',0x300))] and combined==0x5500
 rows.append(dict(width=width,height=height,full_luma_and_subsampled_chroma_crop_exact=True,ds4_depth_10_bits=True,round_bits_zero=True,
  round_pattern=3,pd10_pack_mode_zero=True,first_ds4_precrop_y_c_r2pd_enable_mask='0x5500'))
r=dict(stage=426,rows=rows,target_create_ds4_precrop_round_and_r2pd_executed=True,register_transport_provider_only=True,
 first_ds4_luma_chroma_register='0xd60',first_ds4_packer_register='0xd6c',precrop_registers=['0xd84','0xda4'],depth_registers=['0xd98','0xdb8'],shared_enable_register='0x4c',
 downstream_gpl_wm_index=5,downstream_gpl_packer_mode=0,downstream_gpl_wm_width_bytes='align(pd10_width * 4, 16)',downstream_gpl_wm_height='pd10_height / 2',
 current_driver_has_no_ds4_dma_registration=True,native_geometry_not_pixel_content_proof=True,original_tuning_private=True,
 phone_accessed=False,passed=True)
(HERE/'producer-geometry-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
