"""Execute complete target striping code; libc memory operations are modelled."""
from pathlib import Path
import hashlib,importlib.util,json,struct
HERE=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('halmachine380',HERE/'hal-machine.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=[];records=[];D=m.DATA;P=m.P
for width,height in [(640,480),(1920,1080),(4608,3456)]:
 for port in [8,9]:
  for cores in [1,2]:
   model=m.Machine();u=model.u;config=bytearray(1216)
   for index in [0,port]:
    offset=index*84;struct.pack_into('<III',config,offset,20,width,height);struct.pack_into('<4I',config,offset+52,width,height,width,height//2)
   struct.pack_into('<I',config,1192,1);u.mem_write(D,bytes(config))
   assert model.call(0x144348,D,0,0x10705,0x10000,D+0x2000,D+0x2010,D+0x2014,phase='create')==0
   context=model.read64(D+0x2000);capacity=model.read32(D+0x2010);bl_capacity=model.read32(D+0x2014);assert 2268<=capacity<0x40000
   params=D+0x3000;iq=D+0x10000;ica1=D+0x12000;ica2=D+0x14000;zoom=D+0x16000;prev_zoom=D+0x18000;out=D+0x20000;metadata=D+0x70000;user=D+0x80000
   u.mem_write(params,struct.pack('<5QI',iq,ica1,ica2,zoom,prev_zoom,cores))
   for target in [zoom,prev_zoom]:u.mem_write(target,struct.pack('<6I',width,height,0,0,width,height))
   guard=bytes([0x5a])*64;u.mem_write(out-64,guard);u.mem_write(out,bytes([0xa5])*capacity);u.mem_write(out+capacity,guard)
   assert model.call(0x1448f0,context,params,out,metadata,user,phase='execute')==0
   assert bytes(u.mem_read(out-64,64))==guard and bytes(u.mem_read(out+capacity,64))==guard
   blob=bytes(u.mem_read(out,capacity));passes=struct.unpack_from('<I',blob,20)[0];assert 1<=passes<=4
   stripes=[struct.unpack_from('<H',blob,428+412*i)[0] for i in range(passes)];used=2268+624*sum(stripes)
   assert all(1<=n<=64 for n in stripes) and used<=capacity
   slug=f'{width}x{height}-port{port}-cores{cores}';(P/(slug+'-config-private.bin')).write_bytes(config);(P/(slug+'-stripe-private.bin')).write_bytes(blob[:used]);(P/(slug+'-iq-private.bin')).write_bytes(bytes(u.mem_read(iq,2584)));(P/(slug+'-metadata-private.bin')).write_bytes(bytes(u.mem_read(metadata,512)))
   records.append(dict(slug=slug,config=str(P/(slug+'-config-private.bin')),stripe=str(P/(slug+'-stripe-private.bin')),iq=str(P/(slug+'-iq-private.bin')),used_bytes=used,capacity=capacity))
   assert len(model.allocations)==3
   assert model.call(0x144988,D+0x2000,phase='destroy')==0 and not model.read64(D+0x2000) and not model.allocations
   assert set(model.providers)<={'0x5b1250','0x5b1290','0x5b13c0','0x5b13d0','0x5b13e0'}
   rows.append(dict(width=width,height=height,output_port=port,max_cores=cores,passes=passes,stripes=stripes,stripe_bytes_used=used,stripe_capacity=capacity,bl_capacity=bl_capacity,instructions=model.instructions,output_canaries_intact=True,context_allocations_freed=True,passed=True))
(P/'striping-cases-private.json').write_text(json.dumps(records,indent=2)+'\n')
report=dict(stage=380,tests=rows,original_create_execute_wrapper_allocator_and_destroy_code_executed=True,
 algorithm_functions_not_mocked=True,only_malloc_free_memset_memcpy_memcmp_providers_modelled=True,allocator_returns_dirty_bytes=True,
 synthetic_zero_iq_disabled_modules_and_full_frame_zoom_fixture=True,firmware_image_processing_not_executed=True,hardware_execution=False,passed=True)
(HERE/'striping-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
