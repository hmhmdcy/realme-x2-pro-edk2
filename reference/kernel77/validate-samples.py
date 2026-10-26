"""Validate hardware gauge reads against power_supply values and sealed logs."""
from pathlib import Path
import gzip,hashlib,json,re,shutil
ref=Path(__file__).resolve().parent; out=Path('/mnt/e/edk2-samurai-out/kernel77')
groups=[]
expected={'gauge-tests.txt':'1d707e4b0c9057e9cdd30e8b05dce478e1ddbb6942a58645f6d9c3d87e147bbf',
          'complete-dmesg.txt':'90c66a444b83be3393fd8ef18bf79a3852ab390f547e1281b9922e1a521b33b7',
          'first-dmesg.txt':'907d880a11852b0fd01025314f23b3ccf586869f3e9075533cc50a828557ae9c',
          'before-dmesg.txt':'3b99ba2f471780cffc31d1b4beebbc05195de4f4e710f698755c1e59ba9eeda3',
          'recheck-first-dmesg.txt':'e03c362c8986cf2038464676806644291376ab8af50571e3b8a227e39c1ae0ec',
          'recheck-samples.txt':'cc08a82de4ad13ecc55327cfa7df942dd4d9d955cb68756f54affbe5c94c3732',
          'recheck-complete-dmesg.txt':'1a221a214d015b4e7b3fa8353a7f72588d4c7054a6547673ee4092db2c36dfe1'}
hashes={}
for name in ['before-dmesg.txt','first-dmesg.txt','complete-dmesg.txt','gauge-tests.txt',
             'recheck-first-dmesg.txt','recheck-complete-dmesg.txt','recheck-samples.txt']:
    compressed=out/(name+'.gz' if 'tests' in name or 'samples' in name else name.replace('.txt','.gz'))
    raw=gzip.decompress(compressed.read_bytes())
    digest=hashlib.sha256(raw).hexdigest()
    if name in expected:assert digest==expected[name],name
    (out/name).write_bytes(raw); (ref/name).write_bytes(raw)
    shutil.copyfile(compressed,ref/compressed.name)
    hashes[name]={'bytes':len(raw),'sha256':digest,'gzip_sha256':hashlib.sha256(compressed.read_bytes()).hexdigest()}
for name,count in [('gauge-tests.txt',30),('recheck-samples.txt',15)]:
    text=(out/name).read_text(); blocks=re.split(r'SAMPLE=\d+\n',text)[1:]
    assert len(blocks)==count
    samples=[]
    for block in blocks:
        psy=dict(re.findall(r'^POWER_SUPPLY_([A-Z_]+)=(.+)$',block,re.M))
        raw={n:int(v) for n,v in re.findall(r'^(\w+) reg=0x[0-9a-f]+ value=(\d+)',block,re.M)}
        assert len(raw)==12 and psy['PRESENT']=='1'
        assert int(psy['CAPACITY'])==raw['state_of_charge'] and 0<=int(psy['CAPACITY'])<=100
        assert abs(int(psy['VOLTAGE_NOW'])-raw['pack_voltage']*1000)<=10000
        assert abs(int(psy['TEMP'])-(raw['temperature']-2731))<=2
        current=raw['average_current'] if raw['average_current']<32768 else raw['average_current']-65536
        assert abs(int(psy['CURRENT_NOW'])-current*1000)<=10000
        for property_name,register in [('CHARGE_FULL','full_capacity'),('CHARGE_NOW','remaining_capacity'),('CHARGE_FULL_DESIGN','design_capacity'),('CYCLE_COUNT','cycle_count')]:
            factor=1 if property_name=='CYCLE_COUNT' else 1000
            assert int(psy[property_name])==raw[register]*factor
        assert 5000000<int(psy['VOLTAGE_NOW'])<10000000 and 0<int(psy['TEMP'])<530
        samples.append({'uptime':float(block.splitlines()[0].split()[0]),'voltage_uv':int(psy['VOLTAGE_NOW']),
                        'temp_decic':int(psy['TEMP']),'current_ua':int(psy['CURRENT_NOW']),
                        'soc':int(psy['CAPACITY']),'status':psy['STATUS']})
    def spread(field):return [min(s[field] for s in samples),max(s[field] for s in samples)]
    groups.append({'file':name,'samples':len(samples),'duration_s':samples[-1]['uptime']-samples[0]['uptime'],
                   'voltage_uv':spread('voltage_uv'),'temp_decic':spread('temp_decic'),
                   'current_ua':spread('current_ua'),'soc':spread('soc'),'statuses':sorted({s['status'] for s in samples})})
    assert text.rstrip().endswith('TAINT\n0')
    before=re.search(r'DSI_(?:AFTER_PANEL_CYCLE|BEFORE_SAMPLING)\n(\d+)',text)
    after=re.search(r'DSI_AFTER_SAMPLING\n(\d+)',text)
    assert before and after and before[1]==after[1],name
    groups[-1]['dsi_messages_after_panel_cycle']=int(after[1])
test=(out/'gauge-tests.txt').read_text()
assert 'PASS real A640 vertex/fragment rasterization: 12 submissions' in test
assert 'Native panel disable/unprepare and prepare/enable cycle passed' in test
logs={}
bad=re.compile(r'\bOops:|\bBUG:|Unable to handle kernel|Unhandled fault|context fault|I2C.*(?:error|failed)|geni_i2c.*(?:error|failed|timeout)',re.I)
for name in ['first-dmesg.txt','complete-dmesg.txt','recheck-first-dmesg.txt','recheck-complete-dmesg.txt']:
    lines=(out/name).read_text().splitlines()
    faults=[l for l in lines if bad.search(l)]
    assert not faults,(name,faults)
    logs[name]={'dsi_worker_messages':sum('dsi_err_worker' in l for l in lines),'kernel_or_i2c_faults':faults}
report={'gauge_standard_read_and_sysfs_units_pass':True,'sample_groups':groups,'logs':logs,
        'gpu_regression_submissions':12,'panel_power_cycles':2,
        'fresh_boot_display_regression_open':True,'charger_control_not_validated':True,'hashes':hashes}
(ref/'hardware-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='hashes'},indent=2))
