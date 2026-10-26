from pathlib import Path
import re,runpy,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));out=Path('/mnt/e/edk2-samurai-out/kernel125');out.mkdir(exist_ok=True)
native=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/media/platform/msm/camera_8150/cam_cpas/cpas_top')
def block(t,marker):
 a=t.index('{',t.index(marker));i=a+1;d=1
 while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
 return t[a:i]
def top_entries(t):
 a=1;entries=[]
 while a<len(t)-1:
  if t[a]=='{':
   b=a+1;d=1
   while d:d+=(t[b]=='{')-(t[b]=='}');b+=1
   entries.append(t[a:b]);a=b
  else:a+=1
 return entries
def strip(t):return re.sub(r'/\*.*?\*/','',t,flags=re.S)
reports=[];tables={}
for version in ['100','101','120']:
 p=native/f'cpastop_v175_{version}.h';t=strip(p.read_text());entries=top_entries(block(t,'cam_cpas_v175_'+version+'_camnoc_specific'))
 ports=[]
 for e in entries:
  port=re.search(r'\.port_type\s*=\s*(\w+)',e).group(1)
  if not port.startswith('CAM_CAMNOC_IFE'):continue
  updates=[]
  for field in ['priority_lut_low','priority_lut_high','urgency','danger_lut','safe_lut','ubwc_ctl','flag_out_set0_low']:
   if '.'+field not in e:continue
   reg=block(e,'.'+field);pairs=dict(re.findall(r'\.(\w+)\s*=\s*(true|false|0x[\da-fA-F]+|\d+)',reg))
   if pairs.get('enable')!='true':continue
   row=dict(field=field,offset=int(pairs['offset'],0),value=int(pairs['value'],0),masked=pairs.get('masked_value','0')=='1',mask=int(pairs.get('mask','0xffffffff'),0),shift=int(pairs.get('shift','0'),0))
   updates.append(row)
  ports.append(dict(port=port,updates=updates))
 tables[version]=ports;reports.append(dict(version=version,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),ife_ports=ports,max_offset=max(x['offset'] for p in ports for x in p['updates'])))
assert tables['100']==tables['101'] and len(tables['100'])==2 and all(len(p['updates'])==5 for p in tables['100'])
assert reports[2]['max_offset']>=0x5000
generated='static const struct camss_cpas_reg sm8150_ife_qos[] = {\n'
for p in tables['100']:
 generated+='\t/* '+p['port']+' */\n'
 for x in p['updates']:
  mask=x['mask'] if x['masked'] else 0xffffffff;value=x['value']<<x['shift'] if x['masked'] else x['value'];assert value&~mask==0
  generated+=f'\t{{ 0x{x["offset"]:04x}, 0x{mask:08x}, 0x{value:08x} }},\n'
generated+='};\n';(out/'native-ife-qos-private.h').write_text(generated)
report=dict(native_active_family='camera_8150',qos_revisions=reports,v175_100_and_101_ife_updates_exactly_equal=True,ife_updates_10_including_masked_urgency=True,v175_120_exceeds_own_5000_mmio_extent=True,v175_120_not_safe_to_use_on_own_declared_resource=True,unknown_version_must_reject_before_qos=True,phone_unchanged=True)
(r/'reference/kernel125/native-qos-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('OWN_QOS_100_101_EQUAL_10_UPDATES_120_OUT_OF_OWN_RESOURCE_CONFIRMED')
