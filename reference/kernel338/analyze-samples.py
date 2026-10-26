from pathlib import Path
import importlib.util,json,re,shutil,struct,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1]
sys.path.insert(0,str(HERE.parent/'kernel337'));from stock_bg import StockBayer
engine=StockBayer(P.parent/'kernel328/stats-source/com.qti.stats.aec.so');samples=P/('samples-'+run)
observation=json.loads((P/('probe-'+run+'-observation.json')).read_text());assert observation['state']['terminal'] and not observation['worker_live'] and observation['state']['summary']['passed']
factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text());mappings=dict(s5kgw1='qtech_s5kgw1',imx471='sunny_imx471',imx319='sunny_imx319',s5k3m5='qtech_s5k3m5sx')
input=bytearray();expected=bytearray();rows=[]
for model,variant in mappings.items():
 packet=(samples/('sample-'+model+'-private.stats')).read_bytes();image=(samples/('sample-'+model+'-private.nv12')).read_bytes()
 log=observation['logs']['capture-stats-'+model+'.log'];match=re.search(r'INPUT code=[0-9a-f]+ width=(\d+) height=(\d+)',log);assert match
 width,height=map(int,match.groups());version,size=struct.unpack_from('<II',packet);assert version==1 and size==len(packet)-8
 kind,flags,n=struct.unpack_from('<HHI',packet,8);assert (kind,flags,n)==(1,0,4104)
 histogram=struct.unpack_from('<1024I',packet,16);assert sum(histogram)==width*height//4
 offset=8+n;kind,flags,n,left,top,rw,rh,cols,gridrows,high,bits=struct.unpack_from('<HHI8H',packet,offset)
 assert kind==2 and flags==0 and (cols,gridrows)==(32,16) and bits==14 and high==16383
 assert n==24+cols*gridrows*24 and offset+n==len(packet)==16424 and len(image)==115200
 assert left+cols*rw<=width and top+gridrows*rh<=height
 weights=next(r['data']['lumaWeight']['weight'] for r in factory[variant]['roots']['Metering'] if r['uid']==106)
 pixels=rw*rh//4;thresholds=[high]*4;engine.region_setup(pixels,bits,thresholds,weights)
 regions=[]
 for index in range(cols*gridrows):
  values=struct.unpack_from('<4I4H',packet,offset+24+index*24);sums,counts=values[:4],values[4:];engine.region(sums,counts,index);regions.append(values)
 grid=engine.pool(cols,gridrows);engine.configure(False,0,0,0);index,luma=engine.cells(200,[cell[0] for cell in grid])
 input.extend(struct.pack('<III4I4fII',3,pixels,bits,*thresholds,*weights,1.,cols,gridrows))
 for values in regions:input.extend(struct.pack('<4I4H',*values))
 expected.extend(struct.pack('<512f2f',*[v for cell in grid for v in cell],index,luma))
 rows.append(dict(model=model,input=[width,height],grid=[cols,gridrows],region=[rw,rh],offset=[left,top],pixels_per_channel=pixels,stats_bytes=len(packet),stats_capacity=22568,
  luma_weight_variant=variant,actual_module_supplier_bound=False,luma=luma,reference_exposure_index=200.,reference_lux_index=index,physical_scene_lux_calibration=False))
(P/'hardware-math-input-private.bin').write_bytes(input);(P/'hardware-math-expected-private.bin').write_bytes(expected)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss337-luma';shutil.copyfile(P/'hardware-math-input-private.bin',stage/'hardware-input-private.bin');results=[]
for architecture in ['host','aarch64']:
 output=P/(architecture+'-hardware-math-private.bin')
 cmd=[str(P.parent/'kernel337/bg-host'),str(P/'hardware-math-input-private.bin'),str(output)] if architecture=='host' else ['chroot',str(SDK),'/private/camss337-luma/bg-aarch64','/private/camss337-luma/hardware-input-private.bin','/private/camss337-luma/hardware-output-private.bin']
 q=subprocess.run(cmd,capture_output=True);assert not q.returncode,(architecture,q.returncode,q.stderr.decode())
 if architecture=='aarch64':shutil.copyfile(stage/'hardware-output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected);different=sum(a!=b for a,b in zip(actual,expected));assert not different,(architecture,different)
 results.append(dict(architecture=architecture,cases=4,raw_bayer_regions=2048,pooled_cells=1024,compared_bytes=len(expected),differing_bytes=different,reused_unchanged337_binary=True))
report=dict(stage=338,run=run,cameras=rows,architectures=results,real_hardware_statistics_verified=True,statistics_layout_matches_oem_input=True,
 original_region_instructions_and_pooling_and_lux_wrapper=True,default_weight_fields_used_without_supplier_binding=True,reference_exposure_index_only=True,
 scene_exposure_index_mode_binding_verified=False,ipa_runtime_lux_integrated=False,installed=False,passed=True)
(HERE/'hardware-statistics-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/('probe-'+run+'-validation.json')).write_text(json.dumps(observation['state']['summary'],indent=2)+'\n');print(json.dumps(report,indent=2))
