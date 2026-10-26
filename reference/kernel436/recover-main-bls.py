from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
original=(HERE.parent/'kernel306/decode-tele-bls.py').read_text()
original=original.replace("raw=(P/'qtech-s5k3m5sx-tuning-private.bin').read_bytes()", "raw=(P.parent/'kernel324/sunny_s5kgw1-tuning-private.bin').read_bytes()")
original=original.replace('a9059286f6acf1c5d76a1f943e9f62bf3358c019f1e0b419c24b073fec56da1b','59238df704a1717d3640da23ff36824c0c6874e41a920548b186bcccb5166b5a')
original=original.replace('tele-','main-').replace('stage=306','stage=436')
exec(compile(original,str(HERE/'main-bls-decoder-generated.py'),'exec'))
report=json.loads((HERE/'main-bls-direct-validation.json').read_text())
roots=json.loads((P/'main-bls-direct-private.json').read_text())['roots']
ife=[r for r in roots if r['name']=='bls12_ife']
values={tuple(l['values']) for r in ife for l in r['leaves']}
assert len(values)==1 and all(r['enabled']==1 for r in ife)
value=next(iter(values));assert value[1:]==(0.,0.,0.,0.)
u16=int(value[0]*4);assert u16==value[0]*4
profile=(P.parent/'kernel435/factory-s5kgw1-private.yaml').read_text()
assert profile.count('  residual_black_subtraction: 0\n')==2
assert profile.count('  range_normalization: 1.0\n')==2
normalized=2048/(1-value[0]/16383)
gain=round(normalized)/2048
corrected=profile.replace('  residual_black_subtraction: 0\n',f'  residual_black_subtraction: {u16}\n').replace('  range_normalization: 1.0\n',f'  range_normalization: {gain}\n')
(P/'bls-corrected-s5kgw1-private.yaml').write_text(corrected)
(P/'main-bls-profile-private.json').write_text(json.dumps(dict(offset_u14=value[0],subtraction_u16=u16,normalization_q11=round(normalized),range_normalization=gain,all_ife_roots_same=True,only_black_subtraction_and_normalization_changed=True,original_sha256=hashlib.sha256(profile.encode()).hexdigest(),corrected_sha256=hashlib.sha256(corrected.encode()).hexdigest()),indent=2))
print(json.dumps(dict(main_ife_roots=len(ife),main_ife_regions=sum(len(r['leaves']) for r in ife),all_ife_roots_same=True,profile_ready=True,independent_factory_parser_pending=True)))
