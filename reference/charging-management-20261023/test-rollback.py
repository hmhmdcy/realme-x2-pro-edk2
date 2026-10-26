"""Execute actual rollback policy offline with a recording hardware boundary."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import tempfile
import time

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('trial',ref/'control-trial.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
original={'registers':{'00':18,'01':45,'02':6,'03':162,'04':104,'05':3,'07':20,'08':22,'09':76,'0f':18,'13':27}}
cases=0
with tempfile.TemporaryDirectory() as tmp:
    ps=Path(tmp);t.live.PSY=ps;t.live.CLIENT=ps/'client'
    def reset():
        for name,value in {'samurai-usb-input/online':'1','samurai-usb-input/current_max':'1500000',
            'samurai-gauge-protection/present':'1','samurai-gauge-protection/health':'Good','bq28z610-0/temp':'276'}.items():
            p=ps/name;p.parent.mkdir(exist_ok=True);p.write_text(value)
        model=copy.deepcopy(original['registers']);model.update({'00':10,'0f':10,'03':49,'08':14})
        writes=[]
        def masked(reg,val):
            mask=t.MASKS[reg];k=f'{reg:02x}';model[k]=(model[k]&~mask)|(val&mask);writes.append((reg,val))
        t.masked=masked;t.live.registers=lambda:dict(model)
        last={'at_monotonic':time.monotonic(),'temp_decic':276,'cell1_uv':4315000,'cell2_uv':4312000,'inherited_ceiling_uv':4362500}
        return model,writes,last
    model,writes,last=reset();t.rollback(original,last);cases+=1
    assert writes[0]==(8,8) and writes[-1]==(8,22) and model==original['registers']
    mutations=[('samurai-usb-input/online','0'),('samurai-usb-input/current_max','850000'),
        ('samurai-gauge-protection/present','0'),('samurai-gauge-protection/health','Unspecified failure'),
        ('bq28z610-0/temp','159'),('bq28z610-0/temp','440')]
    for path,value in mutations:
        model,writes,last=reset();(ps/path).write_text(value)
        try:t.rollback(original,last)
        except (AssertionError,OSError):pass
        else:raise AssertionError(('unsafe restoration accepted',path,value))
        assert model['08']&0x18==8 and writes==[(8,8)];cases+=1
    for field,value in [('temp_decic',159),('temp_decic',440),('cell1_uv',4410001),('cell2_uv',4410001),
        ('at_monotonic',time.monotonic()-10),('inherited_ceiling_uv',4350000)]:
        model,writes,last=reset();last[field]=value
        try:t.rollback(original,last)
        except AssertionError:pass
        else:raise AssertionError(('unsafe sample accepted',field,value))
        assert model['08']&0x18==8 and writes==[(8,8)];cases+=1
    for reg in ['01','05','07','09']:
        model,writes,last=reset();model[reg]^=1
        try:t.rollback(original,last)
        except AssertionError:pass
        else:raise AssertionError(('unexpected unowned state accepted',reg))
        assert model['08']&0x18==8 and writes==[(8,8)];cases+=1
    for temp in [160,439]:
        model,writes,last=reset();last['temp_decic']=temp;(ps/'bq28z610-0/temp').write_text(str(temp))
        t.rollback(original,last);assert model==original['registers'];cases+=1
    # A write failure at each restore step must never reach final CHG_EN.
    for fail in range(7):
        model,writes,last=reset();original_masked=t.masked
        def fail_masked(reg,value):
            if len(writes)==fail:raise OSError(5,'injected restore I2C error')
            original_masked(reg,value)
        t.masked=fail_masked
        try:t.rollback(original,last)
        except OSError:pass
        else:raise AssertionError(('write fault not propagated',fail))
        assert (8,22) not in writes;cases+=1
result={'passed':True,'cases':cases,'executed_actual_rollback_policy':True,
    'physical_i2c_boundary':'recording mock; does not validate real writes',
    'source_sha256':hashlib.sha256((ref/'control-trial.py').read_bytes()).hexdigest()}
(ref/'rollback-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
