"""Check observed PD10 packing; scene filtering comparison is approximate."""
from pathlib import Path
import itertools,json
import host,pd10
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'capture-collected-r6'
rows=[];matrix=[[0.0]*4 for _ in range(4)];count=0;reserved_frames=0
for model in ['s5kgw1','s5k3m5','imx471','imx319']:
 for kind in ['pattern','scene']:
  for path in (root/(model+'-'+kind)).glob('ds4-*.bin'):
   _,reserved=pd10.components(path.read_bytes());assert not reserved;reserved_frames+=1
 p=root/(model+'-pattern')
 common=sorted(set(int(x.stem.split('-')[1]) for x in p.glob('full-*.bin'))&set(int(x.stem.split('-')[1]) for x in p.glob('ds4-*.bin')));assert common
 seq=common[0];full=(p/('full-'+str(seq)+'.bin')).read_bytes();raw=(p/('ds4-'+str(seq)+'.bin')).read_bytes();groups,_=pd10.components(raw)
 # The main sensor's Shade Color Bars have a vertical gradient, so they
 # cannot establish a constant input value over the unknown filter support.
 # Sony colour bars also have different widths from Samsung colour bars.
 errors=[]
 if model!='s5kgw1':
  for gy in range(4,56):
   for gx in range(4,76):
    x=gx*8;y=gy*8
    ys=[full[(y+yy)*640+x+xx] for yy in range(-12,20,4) for xx in range(-12,20,4)]
    us=[full[307200+((y+yy)//2)*640+((x+xx)//2)*2] for yy in range(-12,20,4) for xx in range(-12,20,4)]
    vs=[full[307200+((y+yy)//2)*640+((x+xx)//2)*2+1] for yy in range(-12,20,4) for xx in range(-12,20,4)]
    if any(max(a)!=min(a) for a in [ys,us,vs]):continue
    g=groups[gy*80+gx]
    errors.append(max(*(abs(q-ys[0]*4) for q in g[:4]),abs(g[4]-us[0]*4),abs(g[5]-vs[0]*4)))
  assert len(errors)>=1000 and max(errors)<=4,(model,len(errors),max(errors))
 row=dict(model=model,pattern_paired_sequence=seq,pattern_constant_neighborhood_groups=len(errors),
  pattern_max_component_difference_from_full_scaled_to_10bit=max(errors) if errors else None,
  main_shaded_pattern_excluded_from_constant_input_test=model=='s5kgw1')
 p=root/(model+'-scene')
 common=sorted(set(int(x.stem.split('-')[1]) for x in p.glob('full-*.bin'))&set(int(x.stem.split('-')[1]) for x in p.glob('ds4-*.bin')));assert common
 seq=common[-1];full=(p/('full-'+str(seq)+'.bin')).read_bytes();raw=(p/('ds4-'+str(seq)+'.bin')).read_bytes();groups,_=pd10.components(raw)
 local=[[0.0]*4 for _ in range(4)];n=0
 for gy in range(4,56):
  for gx in range(4,76):
   ref=[]
   for target in range(4):
    dy,dx=divmod(target,2);x=(gx*2+dx)*4;y=(gy*2+dy)*4
    ref.append(sum(full[(y+yy)*640+x+xx] for yy in range(4) for xx in range(4))/4)
   for source in range(4):
    for target in range(4):local[source][target]+=(groups[gy*80+gx][source]-ref[target])**2
   n+=1
 scores=sorted((sum(local[perm[target]][target] for target in range(4))/(n*4),perm) for perm in itertools.permutations(range(4)))
 assert scores[0][1]==(0,2,1,3),(model,scores[:3])
 count+=n
 for i in range(4):
  for j in range(4):matrix[i][j]+=local[i][j]
 row.update(scene_paired_sequence=seq,scene_reference_groups=n,scene_raster_field_order=list(scores[0][1]),
  scene_best_mse=scores[0][0],scene_second_mse=scores[1][0],passed=True);rows.append(row)
 y,u,v,_=pd10.planes(raw);pd10.render(y,u,v,160,120,P/(model+'-pd10-scene-4x-private.png'),scale=4)
 uv=full[307200:];pd10.render(list(full[:307200]),list(uv[0::2]),list(uv[1::2]),640,480,P/(model+'-full-scene-private.png'),depth=8)
scores=sorted((sum(matrix[perm[target]][target] for target in range(4))/(count*4),perm) for perm in itertools.permutations(range(4)))
assert scores[0][1]==(0,2,1,3) and reserved_frames==144
r=dict(stage=428,observed_sm8150_pd10_six_msb_bytes_then_little_endian_12_lsb_bits=True,
 low_two_bits_per_component_in_same_order=True,stored_group_order=['Y00','Y10','Y01','Y11','Cb','Cr'],
 raster_luma_field_order=[0,2,1,3],best_among_24_scene_permutations_for_each_camera=True,
 scene_reference_is_approximate_4x4_area_not_exact_ds4_filter=True,scene_best_mse=scores[0][0],scene_second_mse=scores[1][0],
 frames_with_reserved_high_nibbles_zero=reserved_frames,rows=rows,
 rendered_private_full_range_bt601_without_tone_adjustment=True,production_ipe_coarse_buffer_consumer_not_yet_connected=True,
 experimental_fourcc_not_reserved_upstream=True,passed=True)
(HERE/'pixel-layout-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
