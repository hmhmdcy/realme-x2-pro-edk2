"""Select each rear camera's retained ordinary-mode factory tone data."""
from pathlib import Path
import copy,hashlib,json,re,struct,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
sys.path.append(str(storage.SDK/'usr/lib/python3.14/site-packages'));import yaml
class NoAliasDumper(yaml.SafeDumper):
 def ignore_aliases(self,data):return True

# Reuse the already verified colour bridge and generic original TMC axes.
main=yaml.safe_load((P.parent/'kernel437/factory-s5kgw1-private.yaml').read_text())
reference=main['modes'][0]['ipe_tone']
ltm_profiles=json.loads((P.parent/'kernel351/mode-profiles-private.json').read_text())
tmc_profiles=json.loads((P.parent/'kernel412/mode-profiles-private.json').read_text())
gamma_profiles=json.loads((P.parent/'kernel350/mode-profiles-private.json').read_text())
bindings=json.loads((P.parent/'kernel343/bound-mode-configs-private.json').read_text())
bls=json.loads((P/'ife-bls-candidates-private.json').read_text())
def leaves(nodes):
 for n in nodes:
  if 'children' in n:yield from leaves(n['children'])
  else:yield n
def choose(nodes,value,axis=0):
 for i,node in enumerate(nodes):
  if value<=node['trigger'][axis+1] or i+1==len(nodes):return node
  if value<nodes[i+1]['trigger'][axis]:raise RuntimeError('Needs parent interpolation')
def flatten(data):
 result=[]
 for v in data.values():result.extend(v if isinstance(v,list) else [v])
 return result
def context(profiles,variant,mode):return next(p for p in profiles[variant] if p['sensor_mode_index']==mode and p['usecase']=='Preview')
rows=[]
for variant,model,old_stage,old_proof in [('sunny_imx319','imx319',299,'factory-bls-export-validation.json'),('qtech_s5k3m5sx','s5k3m5',306,'tele-bls-export-validation.json')]:
 base=yaml.safe_load((P/('formal-'+model+'-private.yaml')).read_text())
 b=next(r for r in bls if r['variant']==variant);proof=json.loads((HERE.parent/('kernel'+str(old_stage))/old_proof).read_text())
 assert proof['source_sha256']==b['source_sha256'] and proof['independent_reader_and_direct_decoder_agree'] and b['all_ife_regions_same'] and b['root_enable_values']==[1]
 assert len(b['offset_thresholds'])==1;offset,*thresholds=b['offset_thresholds'][0];assert thresholds==[0.,0.,0.,0.]
 ds4_roots=json.loads((P.parent/'kernel426'/(variant+'-ds4-reserves-private.json')).read_text());ds4_selected=json.loads((P.parent/'kernel426'/(variant+'-ds4-selection-private.json')).read_text())
 gtm_roots=json.loads((P.parent/'kernel432'/(variant+'-gtm-trees-private.json')).read_text());gtm_selected=json.loads((P.parent/'kernel431'/(variant+'-gtm-selections-private.json')).read_text())
 for item in base['modes']:
  size=[item['match']['width'],item['match']['height']]
  bound=next(b for b in bindings if b['variant']==variant and b['usecase']=='Preview' and b['sensor_size']==size);mode=bound['sensor_mode_index']
  lp=context(ltm_profiles,variant,mode)['modules'];tp=context(tmc_profiles,variant,mode)['modules'];gamma=context(gamma_profiles,variant,mode)['root']
  ltm,tmc,tmc10=lp['ltm13_ipe'],tp['tmc11_sw'],tp['tmc10_sw']
  assert all(n['matrix']==[1,0,0,0,1,0,0,0,1] and n['offsets']==[0,0,0] for n in leaves(lp['cc13_ipe']['core']))
  ltm_drc=choose(ltm['core'],1);tmc_drc=choose(tmc['core'],1)
  assert ltm['control_method'][1] in [0,1,2] and tmc['control_method'][1] in [0,1,2]
  ltm_hdr=choose(ltm_drc['children'],1,2*ltm['control_method'][1]);tmc_hdr=choose(tmc_drc['children'],1,2*tmc['control_method'][1])
  assert tmc['reserve']['curve_model']==2 and tmc['reserve']['curve_order']==5
  ltm_leaves=ltm_hdr['children'];tmc_leaves=tmc_hdr['children']
  assert gamma['control_method'][1] in [0,1,2]
  g=choose(gamma['core'],1);g=choose(g['children'],1,2*gamma['control_method'][1]);g=next(n for n in g['children'] if n['trigger']==[0])
  gamma_leaves=[]
  for aec in g['children']:
   assert len(aec['children'])==1;cct=aec['children'][0];assert len(cct['children'])==1
   channel=cct['children'][0];assert channel['channel']==3 and len(channel['table'])==257
   gamma_leaves.append(dict(trigger=aec['trigger'],data=channel['table']))
  r=ltm['reserve'];curves=item['gamma']['curves'];assert curves[0]==curves[1]==curves[2]
  end_base=min(int(curves[1][63]+.5),1023);end_next=min(int(curves[1][64]+.5),1024);endpoint=end_base+max(-512,min(511,end_next-end_base))
  tone=dict(enabled=True,mode='factory',input_policy='single-exposure-linear-ae-no-face',input_transfer='ife-green-common-rgb',parent_axes='single-drc-single-hdr-led-off-cct-invariant',
   ltm_aec_control=ltm['control_method'][0],tmc_aec_control=tmc['control_method'][0],gamma_aec_control=gamma['control_method'][0],
   tmc_uid=tmc['uid'],tmc_enabled=tmc['enabled'],tmc_use_ltm=tmc['reserve']['use_ltm'],tmc_use_gtm=tmc['reserve']['use_gtm'],tmc10_enabled=tmc10['enabled'],tmc10_use_ltm=tmc10['reserve']['use_ltm'],
   rgb2y=[r[k] for k in ['c1','c2','c3','c4']],flags=[r[k] for k in ['igamma_en','la_en','mask_filter_en','data_collect_en','img_process_en']],
   weights=r['wt_tab'],mask_kernel=r['mask_filter_kernel_tab'],mask_curve=r['mask_rect_curve_tab'],reserve_curve=r['ltm_curve_tab'],lce_threshold=r['lce_thd'],manual_curve=r['ltm_scale_manual_curve_enable'],ife_forward_endpoint=float(endpoint),
   colour=copy.deepcopy(reference['colour']),tmc_gamma=copy.deepcopy(reference['tmc_gamma']),histogram_log_weights=copy.deepcopy(reference['histogram_log_weights']),contrast_axis=copy.deepcopy(reference['contrast_axis']),
   ltm_regions=[dict(trigger=a['trigger'],data=flatten(a['data'])) for a in ltm_leaves],tmc_regions=[dict(trigger=a['trigger'],data=flatten(a['data'])) for a in tmc_leaves],gamma_regions=gamma_leaves)
  chosen=next(x[2] for x in gtm_selected if x[0]=='gtm10_ife' and x[1]==[0,mode,0,0,0,0,0]);gtm=next(x for x in gtm_roots if x['tag']=='gtm10_ife' and x['uid']==chosen['uid'])
  assert gtm['enabled']==int(bool(tmc['enabled'] and tmc['reserve']['use_gtm']))
  tone['ife_gtm']=dict(enabled=bool(gtm['enabled']),uid=gtm['uid'],model='tmc11-model2',manual_curve=gtm['reserve']['manual_curve_enable'],v2_enable=gtm['reserve']['v2_enable'],**{k:copy.deepcopy(reference['ife_gtm'][k]) for k in ['normalized_axis','integer_axis','contrast_axis']})
  ds=next(x for x in ds4_selected if x['sensor_mode_index']==mode and x['usecase']=='Preview' and x['tag']=='ds4to1v10_ife_full_dc4');dsr=next(x for x in ds4_roots if x['uid']==ds['uid']);assert dsr['passes'][0][0]==0
  item['ife_ds4']=dsr['passes'][0][1:];item['ipe_tone']=tone
  item['residual_black_subtraction']=int(offset*4);item['range_normalization']=round(2048/(1-offset/16383))/2048
  rows.append(dict(model=model,sensor_size=size,sensor_mode_index=mode,ltm_uid=ltm['uid'],tmc11_uid=tmc['uid'],gtm_uid=gtm['uid'],ds4_uid=ds['uid'],tmc10_original_enabled=tmc10['enabled'],tmc11_original_enabled=tmc['enabled'],ipe_ccm_identity_verified=True,original_bls_restored=True,ltm_regions=len(ltm_leaves),tmc_regions=len(tmc_leaves),gamma_regions=len(gamma_leaves)))
 data=yaml.dump(base,Dumper=NoAliasDumper,sort_keys=False).encode();(P/('factory-'+model+'-private.yaml')).write_bytes(data)
 print(json.dumps(dict(model=model,profile_prepared=True,bytes=len(data))),flush=True)
r=dict(stage=438,profiles=rows,independent_original_mode_selection_reused=True,generic_tmc_axes_and_colour_bridge_reused=True,per_camera_factory_ltm_tmc_gamma_gtm_ds4_selected=True,original_bls_crosschecks_reused=True,front_not_forced_into_rear_colour_chain=True,phone_files_unchanged=True,passed=True)
(HERE/'rear-profile-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
