"""Compare the portable adjustment against complete retained OEM instructions."""
from pathlib import Path
import copy, hashlib, importlib.util, json, math, shutil, struct, subprocess
from stock_antibanding import StockAntibanding

HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel358');P.mkdir(exist_ok=True)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
stage=storage.mounted_build().parent/'aec358-tests';stage.mkdir(exist_ok=True)
library=P.parent/'kernel328/stats-source/com.qti.stats.aec.so'
engine=StockAntibanding(library)
factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text())
policies={};source_tables=0
for variant,bundle in factory.items():
    for root in bundle['roots']['Arbitration']:
        data=root['data']
        for table_id,table in enumerate(data['expTables']):
            source_tables+=1
            key=struct.pack('<fIQ',table['thresAntiBandingMinExpTimePct'],data['antibandingVsFPSMethod'],data['minPreviewVertBlankTime'])
            policy=policies.setdefault(key,dict(threshold=table['thresAntiBandingMinExpTimePct'],method=data['antibandingVsFPSMethod'],blanking=data['minPreviewVertBlankTime'],knees={},sources=[]))
            policy['sources'].append(dict(variant=variant,arbitration_uid=root['uid'],table_index=table_id))
            for knee in table['expKneeEntries']:
                policy['knees'][struct.pack('<fQ',knee['gain'],knee['expTime'])]=knee

cases=[];input_data=bytearray();expected=bytearray();keys=set();native_count=0
branch_witness={}
def add(config,exposure,label,valid=True):
    global native_count
    packed=struct.pack('<IQffQQQIfQf',config['enabled'],config['period'],config['threshold'],config['min_gain'],config['min_ns'],config['max_ns'],config['blanking'],config['method'],exposure['gain'],exposure['time'],exposure['index'])
    assert len(packed)==64
    if packed in keys:return
    keys.add(packed)
    if valid:
        before=engine.visited.copy()
        gain,time=engine.adjust(config,exposure)
        expected.extend(struct.pack('<IfQf',1,gain,time,exposure['index']));native_count+=1
        for address in engine.visited-before:branch_witness[hex(address)]=len(cases)
    else:
        expected.extend(bytes(20))
    cases.append(dict(label=label,config=config,exposure=exposure,expected_valid=valid))
    input_data.extend(packed)

base=dict(enabled=1,period=10000000,threshold=1.,min_gain=1.,min_ns=1000,max_ns=33333333,blanking=2000000,method=0)
exposure=dict(gain=4.,time=15000000,index=17.25)
for i,policy in enumerate(policies.values()):
    for period in [10000000,8333333]:
        config=dict(base,period=period,threshold=policy['threshold'],method=policy['method'],blanking=policy['blanking'])
        for maximum in [8333333,16666667,33333333,100000000]:
            config['max_ns']=maximum
            for knee in policy['knees'].values():
                add(config.copy(),dict(gain=knee['gain'],time=knee['expTime'],index=knee['expIndex']),f'factory-policy-{i}')

# Exercise boundaries and policy branches independently of which stock tuning
# roots happen to use them. The OEM, not a second rewrite, supplies all outputs.
for method in [0,1,2]:
    for period in [10000000,8333333]:
        for threshold in [0.,.5,1.,1.5]:
            times={1,period//2,period-1,period,period+1,period*3//2,period*2-1,period*2,period*2+1,period*5//2,period*4+1}
            for gain in [.5,1.,1.5,2.,4.,16.]:
                for maximum in [period-1,period,period*2-1,period*3,period*5]:
                    config=dict(base,method=method,period=period,threshold=threshold,max_ns=maximum,blanking=period//2)
                    for time in times:
                        add(config,dict(exposure,gain=gain,time=time),'synthetic-policy-boundary')
config=dict(base,enabled=0,period=0)
add(config,exposure,'disabled-without-period')
# Above and below the float threshold can map to the same float time. Preserve
# that behavior rather than replacing the comparison with integer arithmetic.
for delta in [-3,-2,-1,0,1,2,3]:
    for time in [100000000+delta,1000000000+delta]:
        add(dict(base,period=100000000,max_ns=2000000000),dict(exposure,time=time),'uint64-to-float-threshold')
for field,value in [('period',0),('threshold',float('nan')),('threshold',-1.),('min_gain',0.),('min_gain',float('inf')),('method',3),('min_ns',40000000)]:
    add(dict(base,**{field:value}),exposure,'invalid-'+field,False)
for field,value in [('gain',0.),('gain',float('nan')),('time',0)]:
    add(base,dict(exposure,**{field:value}),'invalid-input-'+field,False)
add(dict(base,period=1,max_ns=2**64-1,blanking=1),dict(exposure,time=10),'overflow-upper-bound',False)
add(dict(base,period=1,max_ns=2**63,blanking=0),dict(exposure,time=2**31),'unsupported-signed-count',False)

(P/'input-private.bin').write_bytes(struct.pack('<I',len(cases))+input_data)
(P/'expected-private.bin').write_bytes(expected)
(P/'cases-private.json').write_text(json.dumps(cases,allow_nan=True)+'\n')
(P/'policies-private.json').write_text(json.dumps([dict(p,knees=list(p['knees'].values())) for p in policies.values()])+'\n')
(P/'branch-witness-private.json').write_text(json.dumps(branch_witness,indent=2)+'\n')
for source in [HERE/'antibanding-runner.cpp',*(HERE/'libipa').glob('*')]:shutil.copyfile(source,stage/source.name)
shutil.copyfile(P/'input-private.bin',stage/'input-private.bin')
rows=[];sdk_stage=SDK/'private/camss358-antibanding';sdk_stage.mkdir(exist_ok=True)
for arch in ['host','aarch64']:
    mounted=False
    try:
        if arch=='aarch64':
            assert not list(sdk_stage.iterdir())
            subprocess.run(['mount','--bind',str(stage),str(sdk_stage)],check=True,capture_output=True);mounted=True
        flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
        command=['g++',*flags,'-I'+str(stage),str(stage/'antibanding-runner.cpp'),str(stage/'aec_antibanding.cpp'),'-o',str(stage/'antibanding-host')] if arch=='host' else ['chroot',str(SDK),'g++',*flags,'/private/camss358-antibanding/antibanding-runner.cpp','/private/camss358-antibanding/aec_antibanding.cpp','-o','/private/camss358-antibanding/antibanding-aarch64']
        q=subprocess.run(command,capture_output=True);(P/(arch+'-build.log')).write_bytes(q.stdout+q.stderr);q.check_returncode()
        command=[str(stage/'antibanding-host'),str(P/'input-private.bin'),str(P/'host-output-private.bin')] if arch=='host' else ['chroot',str(SDK),'/private/camss358-antibanding/antibanding-aarch64','/private/camss358-antibanding/input-private.bin','/private/camss358-antibanding/aarch64-output-private.bin']
        q=subprocess.run(command,capture_output=True,timeout=30);(P/(arch+'-run.log')).write_bytes(q.stdout+q.stderr);q.check_returncode()
        actual=(P/'host-output-private.bin').read_bytes() if arch=='host' else (stage/'aarch64-output-private.bin').read_bytes()
        assert len(actual)==len(expected)
        differences=[i for i in range(len(cases)) if actual[i*20:(i+1)*20]!=expected[i*20:(i+1)*20]]
        (P/(arch+'-differences-private.json')).write_text(json.dumps([dict(cases[i],actual=list(struct.unpack_from('<IfQf',actual,i*20)),expected=list(struct.unpack_from('<IfQf',expected,i*20))) for i in differences],allow_nan=True)+'\n')
        rows.append(dict(architecture=arch,cases=len(cases),compared_bytes=len(expected),differing_records=len(differences),passed=not differences))
        print(json.dumps(rows[-1]),flush=True)
    finally:
        if mounted:subprocess.run(['umount',str(sdk_stage)],check=True,capture_output=True)
report=dict(stage=358,factory_tables=source_tables,unique_tuning_policies=len(policies),oem_full_function=[hex(engine.begin),hex(engine.end)],
    original_calls=engine.calls,original_instructions=engine.instructions,logging_calls_stubbed=engine.stub_calls,
    arithmetic_calls_stubbed=False,android_algorithm_not_started=True,architectures=rows,
    sensor_line_gain_and_frame_limit_integration_pending=True,ipa_integrated=False,phone_changed=False,passed=all(r['passed'] for r in rows))
(HERE/'antibanding-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
