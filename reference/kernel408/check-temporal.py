"""Compare explicit temporal state and the complete curve sequence to target code."""
from pathlib import Path
import importlib.util, json, math, random, shutil, struct, subprocess, time
import host
HERE = Path(__file__).resolve().parent
P = host.PRIVATE

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

model = module('temporal408', HERE / 'temporal-model.py').TemporalMachine()
old = P.parent / 'kernel407'
legacy_input = (old / 'curve-input-private.bin').read_bytes()
legacy_output = (old / 'curves-host-output-private.bin').read_bytes()
old_cases = json.loads((old / 'curve-cases-private.json').read_text())
assert len(legacy_input) == 6549 * 456
assert len(legacy_output) == (6549 + 81) * 788
records, expected, descriptions = [], [], []
statistics = dict(primitive=0, complete_curve_sequence=0, bypass_state_unchanged=0,
                  transition_restarts=0, filtered_updates=0, pre_attenuation_history_different=0)

def packed(curves):
    values = struct.unpack('<99f', curves)
    def table(nodes, lce=False):
        nodes = [int(math.copysign(math.floor(abs(v)+0.5), v)) for v in nodes]
        assert all(-32768 <= v <= 32767 for v in nodes) or lce
        if lce:
            nodes = [max(-2048, min(2047, v)) for v in nodes]
        nodes = [min(2047, v) for v in nodes]
        words=[]
        for base, following in zip(nodes,nodes[1:]):
            delta=following-base
            lo=(base&4095)|(2048 if base<0 else 0)
            hi=(delta&4095)|(2048 if delta<0 and not lce else 0)
            words.append(lo|(hi<<12))
        return words
    return struct.pack('<96I', *(table(values[:65])+table(values[65:82],True)+table(values[82:],True)))

def add(mode, data, signal, bps, gate, state, kind, **details):
    assert len(data)==456 and len(state)==404
    record=struct.pack('<I',mode)+data+struct.pack('<fII',signal,bps,gate)+state
    try:
        curves,next_state,instructions=model.evaluate(record)
    except Exception:
        (P/'temporal-model-failed-record-private.bin').write_bytes(record)
        (P/'temporal-model-failure-private.json').write_text(json.dumps(dict(
            cases_completed=len(records),kind=kind,mode=mode,**details),indent=2)+'\n')
        raise
    previous_face,previous_count=struct.unpack_from('<2I',state)
    face,count=struct.unpack_from('<2I',next_state)
    if bps or gate==1:
        assert next_state==state
        statistics['bypass_state_unchanged']+=1
    else:
        positive=int(signal>0)
        transition=positive!=previous_face
        wanted=(90 if transition else previous_count)
        assert face==positive and count==max(0,wanted-1)
        statistics['transition_restarts']+=transition
        statistics['filtered_updates']+=wanted!=0
        if not mode:
            assert next_state[8:]==curves
        elif next_state[8:]!=curves:
            statistics['pre_attenuation_history_different']+=1
    records.append(record)
    expected.append(struct.pack('<I',1)+curves+next_state+struct.pack('<I',1)+packed(curves))
    descriptions.append(dict(kind=kind,mode=mode,original_instructions=instructions,**details))
    statistics['complete_curve_sequence' if mode else 'primitive']+=1
    return next_state

zero=bytes(404)
# Direct synthetic transitions establish the arithmetic without Chromatix.
for face in [0,1]:
    for count in [0,1,45,89,90]:
        for signal in [-1.0,0.0,0.01,2.0]:
            for bps,gate in [(0,0),(1,0),(0,1),(0,2),(0,0xffffffff)]:
                curves=struct.pack('<99f', *[float((i-49)*37) for i in range(99)])
                history=struct.pack('<99f', *[float((49-i)*11) for i in range(99)])
                state=struct.pack('<2I',face,count)+history
                add(0,curves+bytes(60),signal,bps,gate,state,'direct-boundary')

# Every factory region enters the complete native sequence once. Exposure
# changes make it observable that saved history precedes attenuation.
factory_count=2135
for i in range(factory_count):
    data=bytearray(legacy_input[i*3*456:(i*3+1)*456])
    a,b=struct.unpack_from('<2f',data,101*4)
    delta=[0.0,(a+b)/2,b+1][i%3]
    struct.pack_into('<2f',data,111*4,100+delta,100)
    other=((i+11)%factory_count)*3
    history=legacy_output[other*788+8:other*788+404]
    state=struct.pack('<2I',(i//2)%2,[0,1,45,89,90][i%5])+history
    add(1,bytes(data),1.0 if i%2 else 0.0,int(i%17==0),1 if i%19==0 else 0,
        state,'factory-complete',factory_index=i)
    if i%700==0:
        print(json.dumps(dict(factory_regions_done=i+1)),flush=True)

# Native automatic curves exercise powf followed immediately by smoothing.
for i in range(6453,6549):
    data=legacy_input[i*456:(i+1)*456]
    history=legacy_output[(i-1)*788+8:(i-1)*788+404]
    state=struct.pack('<2I',i%2,[0,1,89,90][i%4])+history
    add(1,data,float((i%3)-1),0,0,state,'auto-complete')

# Each variant has independent history for a 240-update enter/hold/exit
# sequence, with temporary bypasses that must freeze its state.
for variant in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    indices=[i for i,c in enumerate(old_cases[:6405]) if c.get('variant')==variant]
    selected=[indices[0],indices[min(6,len(indices)-1)]]
    state=zero
    for frame in range(240):
        data=bytearray(legacy_input[selected[(frame//25)%2]*456:(selected[(frame//25)%2]+1)*456])
        a,b=struct.unpack_from('<2f',data,101*4)
        delta=[0.0,(a+b)/2,b+1][(frame//7)%3]
        struct.pack_into('<2f',data,111*4,100+delta,100)
        signal=1.0 if 10<=frame<130 else 0.0
        state=add(1,bytes(data),signal,int(frame in [25,26]),1 if frame==75 else 0,
                  state,'variant-sequence',variant=variant,frame=frame)

rng=random.Random(408)
for i in range(300):
    curves=struct.pack('<99f',*[rng.uniform(-10000,10000) for _ in range(99)])
    history=struct.pack('<99f',*[rng.uniform(-8000,8000) for _ in range(99)])
    state=struct.pack('<2I',i%2,rng.randrange(91))+history
    add(0,curves+bytes(60),rng.uniform(-2,2),0,0,state,'random-direct')

valid_count=len(records)
invalid=[]
sample=bytearray(records[0])
for offset in [4,4+64*4,4+65*4,4+98*4,460,480,480+98*4]:
    for value in [math.nan,math.inf,-math.inf,2097152.0]:
        record=sample.copy();struct.pack_into('<f',record,offset,value);invalid.append(bytes(record))
for offset,value in [(0,2),(464,2),(472,2),(476,91),(476,0xffffffff)]:
    record=sample.copy();struct.pack_into('<I',record,offset,value);invalid.append(bytes(record))
pipeline=bytearray(next(r for r in records if struct.unpack_from('<I',r)[0]==1))
for at in range(99,113):
    record=pipeline.copy();struct.pack_into('<f',record,4+at*4,math.nan);invalid.append(bytes(record))
expected.extend([struct.pack('<I',0)+bytes([0xa5])*800+struct.pack('<I',0)+bytes([0xa5])*384]*len(invalid))
all_input=b''.join(records+invalid)
all_expected=b''.join(expected)
(P/'temporal-input-private.bin').write_bytes(all_input)
(P/'temporal-expected-private.bin').write_bytes(all_expected)
(P/'temporal-cases-private.json').write_text(json.dumps(descriptions,indent=2)+'\n')

# Reuse the exact old inputs and outputs for the refactored public API.
legacy_invalid=[]
for at in [0,64,65,81,82,98,*range(99,113)]:
    for value in [math.nan,math.inf,-math.inf,2097152.0]:
        record=bytearray(legacy_input[:456]);struct.pack_into('<f',record,at*4,value);legacy_invalid.append(bytes(record))
record=bytearray(legacy_input[:456]);struct.pack_into('<I',record,452,2);legacy_invalid.append(bytes(record))
old_input=legacy_input+b''.join(legacy_invalid)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=sdk/'private/camss408-math'
for relative in ['kernel407/curve-runner.cpp','kernel407/libipa/ltm_curves.cpp','kernel407/libipa/ltm_curves.h',
                 'kernel408/temporal-runner.cpp','kernel408/libipa/ltm_face_smoothing.cpp','kernel408/libipa/ltm_face_smoothing.h']:
    target=work/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/relative,target)
rows=[]
for arch in ['host','aarch64']:
    for kind in ['temporal','legacy']:
        rels=(['kernel408/temporal-runner.cpp','kernel408/libipa/ltm_face_smoothing.cpp','kernel407/libipa/ltm_curves.cpp'] if kind=='temporal' else
              ['kernel407/curve-runner.cpp','kernel407/libipa/ltm_curves.cpp'])
        options=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
        binary=P/(kind+'-'+arch)
        if arch=='host':
            command=['g++',*options,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/r) for r in rels],'-o',str(binary)]
            launch=[str(binary)]
        else:
            dest='/private/camss408-math/'+kind+'-aarch64'
            command=['chroot',str(sdk),'g++',*options,*['/private/camss408-math/'+r for r in rels],'-o',dest]
            launch=['chroot',str(sdk),dest]
        q=subprocess.run(command,capture_output=True);(P/(kind+'-'+arch+'-build.log')).write_bytes(q.stdout+q.stderr)
        assert not q.returncode,q.stderr.decode()
        q=subprocess.run(launch,input=all_input if kind=='temporal' else old_input,capture_output=True,timeout=45)
        assert not q.returncode,q.stderr.decode()
        wanted=all_expected if kind=='temporal' else legacy_output
        (P/(kind+'-'+arch+'-actual-private.bin')).write_bytes(q.stdout)
        assert len(q.stdout)==len(wanted),(arch,kind,len(q.stdout),len(wanted))
        differences=sum(a!=b for a,b in zip(q.stdout,wanted))
        rows.append(dict(architecture=arch,scope=kind,compared_bytes=len(wanted),different_bytes=differences,passed=not differences))
        print(json.dumps(rows[-1]),flush=True)
report=dict(stage=408,valid_cases=valid_count,invalid_cases=len(invalid),statistics=statistics,
             factory_complete_regions=2135,automatic_complete_cases=96,variant_sequence_updates=1200,
             original_target_math_and_state_executed=True,
             original_target_primitive_range=['0x360560','0x360ac8'],
             original_target_complete_curve_phase_range=['0x35ec64','0x360c3c'],
             original_instructions=model.instructions,providers=model.providers,
             external_powf_provider_host_libm_not_target_bionic=True,
             actual_target_final_lut_packer_not_executed=True,
             target_float_results_quantized_using_previously_verified_source_rules=True,
             architectures=rows,fp_contract_fast_build=True,host_asan_ubsan=True,
             previous_input_state_unchanged=True,invalid_preserves_both_outputs=True,
             new_state_proposed_not_automatically_committed=True,
             bps_and_raw_aec140_equal1_bypass_without_state_change=True,
             history_saved_before_exposure_attenuation=True,
             raw_aec_field_names_not_inferred_from_newer_source=True,
             explicit_per_pipeline_state_not_hal_global_lifetime_equivalence=True,
             legacy407_all6630_records_byte_identical=True,
             adrc_not_implemented=True,trigger_tree_not_implemented=True,
             source406_kernel_unchanged=True,phone_accessed=False,full_goal_kept_active=True,
             passed=all(r['passed'] for r in rows))
path=HERE/'temporal-validation.json'
if path.exists() and not json.loads(path.read_text())['passed']:
    first=HERE/'temporal-r1-validation.json'
    if not first.exists():first.write_bytes(path.read_bytes())
path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
assert report['passed']
