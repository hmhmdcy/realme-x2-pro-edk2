"""Actual worker validation and zero-load behavior during low-SOC recharge."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual_timer_low_start',HERE/'worker.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
s=dict(shadow=0,valid=1,online=1,protection_ok=1,age_ms=500,thermal_band=4,session_seconds=200,
    cell1_uv=3800000,cell2_uv=3803000,pack_uv=7603000,cycle_timeout=0,error=0,latched=0,
    fault=0,stop_error=0,thermal_inhibit=0,source_inhibit=0,gauge_charge_stop=0)
v=dict(boottime=1000.,read_seconds=.06,sample=s,protection_health='Good',charger_health='Good',
    capacity=13,current_avg_ua=80000,
    protection=dict(id=0x2719,safety=0,pf=0,error=0,operation=902,manufacturing=24),
    source=dict(online='1',usb_type='Unknown [SDP] DCP CDP C',current_max='500000',input_current_limit='500000'),
    caps=dict(input_current_limit=500000,constant_charge_current=250000,constant_charge_voltage=8725000))
io=w.IO.__new__(w.IO);io.deadline=37000.;io.now=lambda:1000.
saved={};io.save=lambda name,value:saved.update({name:value})
cases=[]
def case(name,changes,expected):
    value=copy.deepcopy(v);changes(value)
    try:io.validate(value)
    except (AssertionError,KeyError,TypeError):assert not expected,name
    else:assert expected,name
    cases.append(name)
case('healthy13_recharging',lambda x:None,True)
case('capacity_below10',lambda x:x.update(capacity=9),False)
assert saved['failure-private.json']['stage']=='validate'
assert saved['failure-private.json']['extra']['failures'][0]['name']=='gauge.capacity'
case('low_SOC_average_zero',lambda x:x.update(current_avg_ua=0),False)
case('low_SOC_average_negative',lambda x:x.update(current_avg_ua=-20000),False)
case('low_SOC_average_missing',lambda x:x.pop('current_avg_ua'),False)
case('low_SOC_cell_low',lambda x:x['sample'].update(cell1_uv=3699000),False)
case('midrange_may_balance',lambda x:x.update(capacity=35,current_avg_ua=-10000),True)
case('real_timeout_does_not_require_positive_recharge',lambda x:(x.update(current_avg_ua=-70000),x['sample'].update(cycle_timeout=1,error=-62,latched=1)),True)
class Child:
    def poll(self):return None
io=w.IO.__new__(w.IO);io.parts=[Child(),Child()];io.load_closed=False;io.ema=None;io.duty=.3;io.now=lambda:1000.
io.save=lambda name,value:None
for soc in [13,25]:
    io.duty=.3;io.balance(dict(capacity=soc,sample=dict(gauge_current_ua=150000,temp_decic=260,cell1_uv=3800000,cell2_uv=3803000)))
    assert io.duty==0,soc
    cases.append('duty_zero_at_'+str(soc))
result=dict(passed=True,cases=cases,actual_validate_and_balance_methods=True,
    phone_accessed=False,hardware_timer_tested=False,real_36000_second_observer_unchanged=True,
    minimum_SOC=10,below20_requires_positive_average_and_each_cell_uv=3700000,
    CPU_duty_zero_through_SOC=25,worker_sha256=hashlib.sha256((HERE/'worker.py').read_bytes()).hexdigest(),
    observer_sha256=hashlib.sha256((HERE.parent/'timeout-observation.py').read_bytes()).hexdigest())
(HERE/'low-start-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
