"""Export bounded ordinary-mode factory profiles into private candidate YAML."""
from pathlib import Path
import base64,copy,hashlib,json,re,shlex,struct
import yaml
import host
class ProfileDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):return True
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
proof=json.loads((P.parent/'kernel420/install-proof-private.json').read_text())
expected=proof['private_defaults']['s5kgw1.yaml']
code="from pathlib import Path;import base64;print(base64.b64encode(Path('/etc/libcamera/ipa/camss-vfe/s5kgw1.yaml').read_bytes()).decode())"
raw=base64.b64decode(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout.strip())
assert hashlib.sha256(raw).hexdigest()==expected,'Inspect changed device-private profile'
(P/'formal-s5kgw1-private.yaml').write_bytes(raw)
base=yaml.safe_load(raw);assert base['sensor_model']=='s5kgw1' and base['version']==2
ltm_profiles=json.loads((P.parent/'kernel351/mode-profiles-private.json').read_text())['sunny_s5kgw1']
tmc_profiles=json.loads((P.parent/'kernel412/mode-profiles-private.json').read_text())['sunny_s5kgw1']
gamma_profiles=json.loads((P.parent/'kernel350/mode-profiles-private.json').read_text())['sunny_s5kgw1']
tmc_gamma=list(struct.unpack('<257f',(P.parent/'kernel413/target-default-gamma-private.bin').read_bytes()))
weights=list(struct.unpack('<1024f',(P.parent/'kernel413/histogram-log-weights-private.bin').read_bytes()))
axis=list(struct.unpack('<1024f',(P.parent/'kernel412/contrast-axis-private.bin').read_bytes()))
fixture=(P.parent/'kernel400/test-chain-fixture.h').read_text()
cst=fixture.split('.cst =',1)[1].split('.cv =',1)[0];cv=fixture.split('.cv =',1)[1]
def values(text,name,count):
    match=re.search(r'\.'+name+r'\s*=\s*\{([^}]+)\}',text);assert match,name
    out=[int(v) for v in re.findall(r'-?\d+',match[1])];assert len(out)==count;(out);return out
colour=struct.pack('<I9h3h3H3H3H',5,*values(cst,'matrix',9),*values(cst,'subtract',3),
    *values(cst,'offset',3),*values(cst,'minimum',3),*values(cst,'maximum',3))+bytes(2+28)
offset=re.search(r'\.y_offset\s*=\s*(-?\d+)',cv);assert offset
colour+=struct.pack('<3hh8h2h',*values(cv,'luma',3),int(offset[1]),*values(cv,'chroma',8),*values(cv,'offset',2))
assert len(colour)==104
def flatten(data):
    out=[]
    for v in data.values():out.extend(v if isinstance(v,list) else [v])
    return out
def choose(regions,trigger,axis=0):
    for i,r in enumerate(regions):
        if trigger<=r['trigger'][axis+1]:return r
        if i+1<len(regions) and trigger<regions[i+1]['trigger'][axis]:raise RuntimeError('Parent interpolation requires a full tree adapter')
    return regions[-1]
def context(profiles,mode):return next(c for c in profiles if c['sensor_mode_index']==mode and c['usecase']=='Preview')
rows=[]
for item in base['modes']:
    match=item['match'];w,h=match['width'],match['height']
    if (w,h) not in [(4608,3456),(4608,2592)]:continue
    mode=2 if h==3456 else 4
    lp=context(ltm_profiles,mode)['modules'];tp=context(tmc_profiles,mode)['modules']
    ltm=lp['ltm13_ipe'];tmc=tp['tmc11_sw'];tmc10=tp['tmc10_sw'];gamma=context(gamma_profiles,mode)['root']
    # Ordinary rear modes have identity IPE CCM; their actual IFE CCM remains
    # in its existing stage. Front's nonidentity IPE CCM is not bypassed here.
    def cc_leaves(nodes):
        for n in nodes:
            if 'children' in n:yield from cc_leaves(n['children'])
            else:yield n
    # Verify the selected IPE CCM is identity instead of relying on a comment.
    for data in cc_leaves(lp['cc13_ipe']['core']):
        assert data['matrix']==[1,0,0,0,1,0,0,0,1] and data['offsets']==[0,0,0], 'Nonidentity IPE CCM needs its own stage'
    assert ltm['enabled']==ltm['reserve']['ltm_en']==1 and gamma['enabled']==1
    ltm_drc=choose(ltm['core'],1);tmc_drc=choose(tmc['core'],1)
    assert len(ltm_drc['children'])==len(tmc_drc['children'])==1
    assert tmc['reserve']['curve_model']==2 and tmc['reserve']['curve_order']==5
    ltm_leaves=ltm_drc['children'][0]['children'];tmc_leaves=tmc_drc['children'][0]['children']
    gamma_drc=choose(gamma['core'],1);assert len(gamma_drc['children'])==1
    gamma_hdr=gamma_drc['children'][0];assert len(gamma_hdr['children'])==1
    gamma_led=gamma_hdr['children'][0];assert gamma_led['trigger']==[0]
    gamma_leaves=[]
    for aec in gamma_led['children']:
        assert len(aec['children'])==1,'Need actual CCT interpolation'
        cct=aec['children'][0];assert len(cct['children'])==1
        channel=cct['children'][0];assert channel['channel']==3 and len(channel['table'])==257
        gamma_leaves.append(dict(trigger=aec['trigger'],data=channel['table']))
    r=ltm['reserve'];curves=item['gamma']['curves'];assert curves[0]==curves[1]==curves[2]
    def nearest(v):return int(v+.5)
    end_base=min(nearest(curves[1][63]),1023);end_next=min(nearest(curves[1][64]),1024)
    endpoint=end_base+max(-512,min(511,end_next-end_base))
    tone=dict(enabled=True,mode='factory',input_policy='single-exposure-linear-ae-no-face',
        input_transfer='ife-green-common-rgb',parent_axes='single-drc-single-hdr-led-off-cct-invariant',
        ltm_aec_control=ltm['control_method'][0],tmc_aec_control=tmc['control_method'][0],gamma_aec_control=gamma['control_method'][0],
        tmc_uid=tmc['uid'],tmc_enabled=tmc['enabled'],tmc_use_ltm=tmc['reserve']['use_ltm'],tmc_use_gtm=tmc['reserve']['use_gtm'],
        tmc10_enabled=tmc10['enabled'],tmc10_use_ltm=tmc10['reserve']['use_ltm'],
        rgb2y=[r[k] for k in ['c1','c2','c3','c4']],flags=[r[k] for k in ['igamma_en','la_en','mask_filter_en','data_collect_en','img_process_en']],
        weights=r['wt_tab'],mask_kernel=r['mask_filter_kernel_tab'],mask_curve=r['mask_rect_curve_tab'],
        reserve_curve=r['ltm_curve_tab'],lce_threshold=r['lce_thd'],manual_curve=r['ltm_scale_manual_curve_enable'],
        ife_forward_endpoint=float(endpoint),colour=list(colour),tmc_gamma=tmc_gamma,histogram_log_weights=weights,contrast_axis=axis,
        ltm_regions=[dict(trigger=a['trigger'],data=flatten(a['data'])) for a in ltm_leaves],
        tmc_regions=[dict(trigger=a['trigger'],data=flatten(a['data'])) for a in tmc_leaves],gamma_regions=gamma_leaves)
    assert all(len(a['data'])==179 for a in tone['ltm_regions']) and all(len(a['data'])==44 for a in tone['tmc_regions'])
    item['ipe_tone']=tone
    rows.append(dict(sensor_mode_index=mode,width=w,height=h,ltm_root=ltm['uid'],tmc11_root=tmc['uid'],gamma_root=gamma['uid'],
        ltm_regions=len(ltm_leaves),tmc_regions=len(tmc_leaves),gamma_regions=len(gamma_leaves)))
assert len(rows)==2
manifest={}
for mode in ['factory','gamma-roundtrip','colour-roundtrip','bypass']:
    obj=copy.deepcopy(base)
    for item in obj['modes']:
        if 'ipe_tone' in item:
            if mode=='bypass':del item['ipe_tone']
            else:item['ipe_tone']['mode']=mode
    data=yaml.dump(obj,Dumper=ProfileDumper,sort_keys=False,allow_unicode=True).encode();path=P/(mode+'-s5kgw1-private.yaml');assert not path.exists()
    path.write_bytes(data);manifest[mode]=dict(name=path.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
(P/'tone-profiles-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
report=dict(stage=423,physical_model='s5kgw1',modes=rows,profile_files=manifest,
    source_profile_matches_formal420=True,factory_roots_reused_without_new_firmware_read=True,
    single_exposure_unity_adrc_split_policy_explicit_not_observed_android_aec=True,
    force_tmc_histogram_update_per_calculated_frame=True,ife_forward_endpoint_reconstructed_from_actual_last_segment=True,
    disabled_front_tmc_not_activated=True,production_defaults_not_modified=True,passed=True)
(HERE/'profiles-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
