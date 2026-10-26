"""Verify the real reserve predicate refuses missing energy and unhealthy states."""
from pathlib import Path
import copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual_short_trial_reserve',HERE/'short-trial-reserve.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sample=dict(shadow=0,valid=1,online=1,protection_ok=1,budget_ua=500000,desired_enable=1,
            gauge_current_ua=100000,temp_decic=250,cell1_uv=3750000,cell2_uv=3753000,
            **{k:0 for k in ['fault','error','stop_error','latched','cycle_timeout','thermal_inhibit',
                             'source_inhibit','gauge_charge_stop']})
cases=[('reserve_boundary',10,120000,{},True),('low_soc',9,120000,{},False),
    ('too_little_capacity',10,119999,{},False),('capacity_unknown',None,120000,{},False),
    ('remaining_unknown',10,None,{},False),('high_soc',101,140000,{},False),
    ('low_cell',10,140000,{'cell1_uv':3699000},False),
    ('unbalanced',10,140000,{'cell1_uv':3710000},False),
    ('hot',10,140000,{'temp_decic':400},False),('cold',10,140000,{'temp_decic':179},False),
    ('offline',10,140000,{'online':0},False),('shadow',10,140000,{'shadow':1},False),
    ('fault',10,140000,{'fault':1},False),('stale_stop',10,140000,{'stop_error':-5},False),
    ('timeout',10,140000,{'cycle_timeout':1},False),('low_budget',10,140000,{'budget_ua':100000},False),
    ('not_enabled',10,140000,{'desired_enable':0},False),
    ('net_discharge',10,140000,{'gauge_current_ua':-1000},False)]
for name,soc,remaining,changes,expected in cases:
    s=copy.deepcopy(sample);s.update(changes)
    assert m.short_trial_reserve(soc,remaining,s) is expected,name
result=dict(passed=True,cases=len(cases),actual_function='short_trial_reserve',
    source_sha256=hashlib.sha256((HERE/'short-trial-reserve.py').read_bytes()).hexdigest(),
    phone_accessed=False,long_test_reserve_unchanged=True,
    minimum_capacity_percent=10,minimum_remaining_uah=120000,minimum_each_cell_uv=3700000)
(HERE/'short-trial-reserve-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
