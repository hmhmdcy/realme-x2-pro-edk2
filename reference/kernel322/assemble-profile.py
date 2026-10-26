"""Select factory LSC at explicit OEM lux-index/CCT; never infer lux from exposure.

Inputs and generated individual meshes remain in the private output directory.
The default branch is explicit; this does not reproduce vendor scene selection.
"""
from pathlib import Path
import copy, importlib.util, json, math, yaml

CHANNELS = ('r', 'gr', 'gb', 'b')

def select(regions, value, positions=(0, 1)):
    if not regions or not math.isfinite(value):
        raise ValueError('finite trigger and nonempty regions required')
    bands = [(r['trigger'][positions[0]], r['trigger'][positions[1]]) for r in regions]
    if any(not math.isfinite(a+b) or a>b for a,b in bands):
        raise ValueError('invalid trigger interval')
    if any(bands[i][1] > bands[i+1][0] for i in range(len(bands)-1)):
        raise ValueError('overlapping trigger intervals')
    for i, (_, end) in enumerate(bands):
        if value <= end or i == len(bands)-1:
            return i, i, 0.
        begin = bands[i+1][0]
        if value < begin:
            return i, i+1, (value-end)/(begin-end)
    raise AssertionError('unreachable')

def mix(a, b, weight):
    return {c: [x+(y-x)*weight for x,y in zip(a[c],b[c])] for c in CHANNELS}

def interpolate(regions, value, leaf, positions=(0,1)):
    a,b,w=select(regions,value,positions)
    first=leaf(regions[a])
    return first if a==b else mix(first,leaf(regions[b]),w)

def assemble(root, lux, cct, led_index=None):
    nodes=root['core']
    # Lens, DRC and HDR each have one branch in these retained profiles.
    # Multiple LED branches require an explicit index; flash blending is separate.
    for _ in range(3):
        if len(nodes)!=1:raise ValueError('additional parent trigger selection required')
        nodes=nodes[0]['children']
    if led_index is None:
        if len(nodes)!=1:raise ValueError('explicit illuminator branch required')
        nodes=nodes[0]['children']
    else:
        branches=[n for n in nodes if n['trigger']==[led_index]]
        if len(branches)!=1:raise ValueError('illuminator branch not available')
        nodes=branches[0]['children']
    gains=interpolate(nodes,lux,lambda n:interpolate(n['children'],cct,lambda r:r['gains']))
    golden=interpolate(root['golden'],cct,lambda r:r['gains'])
    return gains,golden

def main():
    here=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('host',here/'host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
    private=host.PRIVATE
    roots=json.loads((private/'decoded-trigger-trees-private.json').read_text())
    selectors=json.loads((here/'trigger-tree-validation.json').read_text())['selectors']
    default=next(r for r in selectors if r['selector']=='Scenario.Default/XML/IFE/lsc34_ife.xml')
    root=next(r for r in roots if r['uid']==default['binary_uids'][0])
    # Explicit diagnostic coordinates; these are not measured current scene values.
    lux,cct=100.,6500.
    gains,golden=assemble(root,lux,cct)
    unit=json.loads((private.parent/'kernel320/stock-unit-lsc-private.json').read_text())['channels']
    assert all(len(v)==221 and all(math.isfinite(x) and x>0 for x in v) for m in [gains,golden,dict(zip(CHANNELS,unit))] for v in m.values())
    directory=private/'profiles';directory.mkdir(exist_ok=True)
    base=yaml.safe_load((here.parent/'kernel313/imx319.yaml').read_text())
    mode=base['modes'][0];mode['residual_black_subtraction']=0;mode['range_normalization']=1.
    (directory/'off.yaml').write_text(yaml.safe_dump(base,sort_keys=False))
    lsc=dict(source_span=[1631.,1223.],first_quad=[0.,0.],quad_step=[2.,2.],gains=gains)
    mode['lens_shading']=lsc
    (directory/'factory.yaml').write_text(yaml.safe_dump(base,sort_keys=False))
    lsc.update(golden=golden,unit=dict(zip(CHANNELS,unit)))
    (directory/'unit.yaml').write_text(yaml.safe_dump(base,sort_keys=False))
    # Independent boundary vectors for the pinned GetIndexPtTrigger convention.
    fixture=[dict(trigger=[1.,10.]),dict(trigger=[20.,30.]),dict(trigger=[40.,50.])]
    vectors=[(-1,(0,0,0.)),(1,(0,0,0.)),(10,(0,0,0.)),(15,(0,1,.5)),(20,(1,1,0.)),(25,(1,1,0.)),(30,(1,1,0.)),(35,(1,2,.5)),(40,(2,2,0.)),(100,(2,2,0.))]
    assert all(select(fixture,v)==expected for v,expected in vectors)
    for invalid in [float('nan'),float('inf')]:
        try:select(fixture,invalid)
        except ValueError:pass
        else:raise AssertionError('nonfinite trigger accepted')
    # Exercise every retained profile at each plateau and interpolation gap.
    cases=0
    for item in roots:
        nodes=item['core']
        for _ in range(4):assert len(nodes)==1;nodes=nodes[0]['children']
        probes={t for n in nodes for t in n['trigger'][:2]}
        probes.update((a['trigger'][1]+b['trigger'][0])/2 for a,b in zip(nodes,nodes[1:]))
        for value in probes:
            for kelvin in [1000.,2300.,2500.,3000.,3550.,4050.,4550.,6500.,12000.]:
                a,b=assemble(item,value,kelvin)
                assert all(len(v)==221 and all(math.isfinite(x) and x>0 for x in v) for m in [a,b] for v in m.values())
                cases+=1
    report=dict(stage=322,selector=default['selector'],equivalent_binary_uids=default['binary_uids'],explicit_lux_index=lux,explicit_cct_kelvin=cct,
        trigger_semantics='plateau within each region; linear only in the gap between regions',boundary_vectors=len(vectors),nonfinite_rejected=True,
        factory_trigger_cases=cases,individual_decode_stage=320,geometry_reference_stage=321,generated_profiles=['off','factory','unit'],
        scene_lux_or_cct_measured=False,factory_checksum_verified=False,default_tuning_changed=False,passed=True)
    (here/'profile-assembly-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
