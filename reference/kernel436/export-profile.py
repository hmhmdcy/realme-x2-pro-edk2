"""Restore the retained GW1 IFE black reference before LSC/tone processing."""
from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
parser=json.loads((HERE/'main-factory-bls-export-validation.json').read_text())
assert parser['independent_reader_and_direct_decoder_agree'] and parser['ife_regions']==10
roots=json.loads((P/'main-bls-direct-private.json').read_text())['roots']
ife=[r for r in roots if r['name']=='bls12_ife'];assert len(ife)==2 and all(r['enabled']==1 for r in ife)
values={tuple(l['values']) for r in ife for l in r['leaves']};assert len(values)==1
offset,*thresholds=values.pop();assert thresholds==[0.,0.,0.,0.]
subtraction=int(offset*4);assert subtraction==offset*4 and 0<subtraction<65536
normalization=round(2048/(1-offset/16383))/2048
original=(P.parent/'kernel435/factory-s5kgw1-private.yaml').read_text()
expected=json.loads((HERE.parent/'kernel435/profile-export-validation.json').read_text())['profile_sha256']
assert hashlib.sha256(original.encode()).hexdigest()==expected
old=['  residual_black_subtraction: 0\n','  range_normalization: 1.0\n']
new=[f'  residual_black_subtraction: {subtraction}\n',f'  range_normalization: {normalization}\n']
corrected=original
for a,b in zip(old,new):assert corrected.count(a)==2;corrected=corrected.replace(a,b)
restored=corrected
for a,b in zip(old,new):restored=restored.replace(b,a)
assert restored==original
out=P/'factory-s5kgw1-private.yaml';out.write_text(corrected)
assert out.read_bytes()==(P/'bls-corrected-s5kgw1-private.yaml').read_bytes()
r=dict(stage=436,original_main_factory_ife_bls_restored=True,original_reader_and_typed_decoder_agree=True,
 all_ife_roots_same=True,ife_roots=2,ife_regions=10,only_black_subtraction_and_normalization_changed=True,
 original_lsc_gtm_tmc_ltm_gamma_colour_and_pd10_fields_unchanged=True,application_pixel_correction=False,
 existing_vfe175_bls_backend_reused=True,individual_dark_calibration_claimed=False,
 profile_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),installed=False,passed=True)
(HERE/'profile-export-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
