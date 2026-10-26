"""Reuse the rear exporter while retaining front block placement and switches."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel438/export-rear-profiles.py').read_text()
def replace(a,b):
 global source
 assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
replace("bls=json.loads((P/'ife-bls-candidates-private.json').read_text())", "bls=json.loads((P.parent/'kernel438/ife-bls-candidates-private.json').read_text())")
replace("for variant,model,old_stage,old_proof in [('sunny_imx319','imx319',299,'factory-bls-export-validation.json'),('qtech_s5k3m5sx','s5k3m5',306,'tele-bls-export-validation.json')]:", "for variant,model,old_stage,old_proof in [('sunny_imx471','imx471',438,'front-factory-bls-export-validation.json')]:")
replace("base=yaml.safe_load((P/('formal-'+model+'-private.yaml')).read_text())", "base=yaml.safe_load((P.parent/'kernel438'/('formal-'+model+'-private.yaml')).read_text())")
replace("  size=[item['match']['width'],item['match']['height']]", "  size=[item['match']['width'],item['match']['height']]\n  if size!=[2304,1728]:continue # No original binding for the separate 1928x1088 crop.")
replace("  assert all(n['matrix']==[1,0,0,0,1,0,0,0,1] and n['offsets']==[0,0,0] for n in leaves(lp['cc13_ipe']['core']))", """  ccm=copy.deepcopy(lp['cc13_ipe'])
  assert mode==1 and ccm['enabled']==1 and not item.get('colour_correction',{}).get('enabled',False)
  assert len(list(leaves(ccm['core'])))==28
  assert any(n['matrix']!=[1,0,0,0,1,0,0,0,1] for n in leaves(ccm['core']))
  for leaf in leaves(ccm['core']):leaf['offsets']=list(map(float,leaf['offsets']))
  assert tmc['enabled']==tmc10['enabled']==0
""")
replace("  item['ife_ds4']=dsr['passes'][0][1:];item['ipe_tone']=tone", """  tone['colour_correction']=dict(enabled=True,qfactor=ccm['qfactor'],aec_control=['lux_index','analogue_gain'][ccm['control_method'][0]],hdr_control=['exposure_time_ratio','sensitivity_ratio','exposure_gain_ratio'][ccm['control_method'][1]],aec_source='runtime',reference_triggers=dict(drc_gain=1.0,hdr_ratio=1.0,led_index=0),core=ccm['core'])
  assert gtm['enabled']==0
  item['ife_ds4']=dsr['passes'][0][1:];item['ipe_tone']=tone""")
replace('ipe_ccm_identity_verified=True',"ipe_ccm_uid=ccm['uid'],ipe_ccm_regions=28,ipe_ccm_factory_tree=True,ife_ccm_disabled=True")
replace('stage=438,profiles=rows','stage=439,profiles=rows')
replace('front_not_forced_into_rear_colour_chain=True','front_tmc_gtm_disabled_preserved=True,unbound_crop_unchanged=True')
replace("HERE/'rear-profile-validation.json'","HERE/'front-profile-validation.json'")
exec(compile(source,str(HERE/'export-front-profile.py'),'exec'))
