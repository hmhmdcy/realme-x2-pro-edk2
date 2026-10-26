from pathlib import Path
import tarfile,json,hashlib,re,collections
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel126')
with tarfile.open(out/'tpg-once-private.tar') as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256(data[n.removeprefix('./')]).hexdigest()==h
assert data['boot-id-private.txt'].strip()==(out/'embedded-boot-id-private.txt').read_bytes().strip()
assert data['capture-exit.txt'].strip()==b'0' and data['dma-trace-after.txt'].strip()==b'N' and data['taint-after.txt'].strip()==b'0'
assert data['sensor-after.txt'].strip()==b'offline\nvdd=0 vddio=0'
capture=data['capture.txt'].decode();assert 'CAPTURE_RESULT success=1 cleanup_complete=1' in capture
frames=[dict(re.findall(r'(\w+)=([0-9a-f]+)',line)) for line in capture.splitlines() if line.startswith('FRAME ')]
assert len(frames)==3 and [int(f['sequence']) for f in frames]==[0,1,2]
assert all(int(f['bytes'])==int(f['changed'])==int(f['active_changed'])==int(f['active_bytes'])==96000 for f in frames)
assert all(int(frames[i]['timestamp_us'])<int(frames[i+1]['timestamp_us']) for i in range(2))
assert len(set(f['hash'] for f in frames))==1
raw=data['first-frame-private.raw'];assert len(raw)==96000 and len(set(raw))>1
value=14695981039346656037
for byte in raw:value=((value^byte)*1099511628211)&((1<<64)-1)
assert f'{value:016x}'==frames[0]['hash']
pixels=[]
for offset in range(0,len(raw),5):
 chunk=raw[offset:offset+5];pixels.extend((chunk[i]<<2)|((chunk[4]>>(2*i))&3) for i in range(4))
assert len(pixels)==76800 and len(set(pixels))>1 and min(pixels)>=0 and max(pixels)<=1023
rows=[pixels[y*320:(y+1)*320] for y in range(240)]
assert all(rows[y]==rows[y%2] for y in range(240)) and all(len(set(row))>1 for row in rows)
before=data['dmesg-before.txt'];after=data['dmesg-after.txt'];assert after.startswith(before);new=after[len(before):].decode()
mappings=[(int(a,16),int(s)) for a,s in re.findall(r'DMA plane 0 address (0x[0-9a-f]+) size (\d+)',new)]
assert len(mappings)==6 and len(set(a for a,s in mappings))==3 and all(s==96000 and 0x07400000<=a<a+s<=0xe0000000 for a,s in mappings)
assert all(word not in new for word in ['Unhandled context fault','Translation fault','*** gpu fault','WARNING:','BUG:','Oops:','CPAS','timeout','failed'])
def interrupts(blob):
 result={}
 for line in blob.decode().splitlines():
  if 'acb3000.camss_msm_' in line:
   fields=line.split();result[fields[-1]]=sum(map(int,fields[1:9]))
 return result
a=interrupts(data['interrupts-before.txt']);b=interrupts(data['interrupts-after.txt']);delta={n:b[n]-a[n] for n in a}
assert delta['acb3000.camss_msm_vfe0']>0 and delta['acb3000.camss_msm_csid0']>0
assert all(v==0 for n,v in delta.items() if n not in ['acb3000.camss_msm_vfe0','acb3000.camss_msm_csid0'])
for name in ['power-before.txt','power-after.txt']:
 text=data[name].decode();assert re.search(r'ife_0_gdsc\s+off-0',text) and re.search(r'ife_1_gdsc\s+off-0',text)
 assert len(re.findall(r'genpd:[012]:acb3000.camss\s+suspended\s+0\s+SW',text))==3
report=dict(actual_native_kernel126_tpg_pass=True,embedded_dtb_prior_verified=True,standard_media_v4l2_ioctls=True,frames=3,width=320,height=240,bytes_per_frame=96000,all_active_bytes_overwrite_distinct_prefill=True,sequence_and_timestamp_monotonic=True,all_three_frame_fnv64=frames[0]['hash'],first_frame_sha256=hashlib.sha256(raw).hexdigest(),raw10_decoded_pixel_count=76800,raw10_levels=sorted(collections.Counter(pixels).items()),nonuniform_horizontal_pattern=True,all240_rows_repeat_two_row_pattern=True,bayer_colour_channel_order_and_full10bit_range_not_claimed=True,three_dma_addresses=[hex(a) for a in sorted(set(a for a,s in mappings))],all_plane_extents_inside_native_window=True,actual_allocation_and_dma_content_verified=True,irq_delta=delta,camss_three_domains_return_to_suspended_zero_users=True,ife_both_domains_off=True,standard_cleanup_calls_succeeded=True,dma_trace_disabled_after=True,taint_after=0,no_new_kernel_fault_in_capture_interval=True,physical_sensor_power_remains_off=True,accepted_native_cpas100_or101_inferred_from_checked_success_path=True,exact_cpas_hw_revision_not_read_back_to_log=True,physical_camera_accepted=False,system_complete=False,goal_complete=False)
(r/'reference/kernel126/tpg-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'tpg-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
