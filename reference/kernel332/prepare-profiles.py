from pathlib import Path
import copy,importlib.util,json,struct,sys
sys.path.append('/usr/lib/python3/dist-packages')
import yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('stock_inverse',HERE.parent/'kernel331/stock_inverse.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
engine=mod.StockInverse(P.parent/'kernel328/stats-source/com.qti.stats.awb.so')
cases=json.loads((P.parent/'kernel330/cases-private.json').read_text())
bundle=json.loads((P.parent/'kernel328/wb-reference-bundle-private.json').read_text())
cal=json.loads((P.parent/'kernel329/calibrated-ratios-private.json').read_text())
(P/'profiles').mkdir(exist_ok=True)
for name,case in cases.items():
 profile=yaml.safe_load((P.parent/'kernel330/profiles'/(name+'.yaml')).read_text())
 raw=next(r['data']['points'][:10] for r in bundle[case['variant']]['factory_roots'] if r['tag']=='refPtV1' and r['uid']==79)
 factors=cal[case['variant']]['factors'] if case['kind']=='unit' else [[1.,1.]]*10
 points=engine.calibrated_points(raw,factors);engine.configure(points)
 case['reference_uid']=79;case['expected_manual_gain_cct']=round(engine.estimate([struct.unpack('<f',struct.pack('<f',1/1.25))[0],struct.unpack('<f',struct.pack('<f',1/.75))[0]])[1])
 for mode in profile['modes']:mode['white_balance_reference']['reference_points']=copy.deepcopy(raw)
 (P/'profiles'/(name+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False))
 (P/(name+'-points-private.bin')).write_bytes(struct.pack('<20f',*[v for row in points for v in row]))
(P/'cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
(HERE/'profile-validation.json').write_text(json.dumps(dict(stage=332,profiles=len(cases),reference_root_uid=79,mwb_root_uid=117,
 calibrated_reference_points=True,default_profiles_changed=False,supplier_binding_verified=False,passed=True),indent=2)+'\n')
print('Prepared optional ten calibrated reference-point profiles.')
