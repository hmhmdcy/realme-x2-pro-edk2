"""Check assembled typed frames against target temporal, inverse and ADRC math."""
from pathlib import Path
import importlib.util,json,math,shutil,struct,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel422')
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
static=module('static422',HERE/'static-model.py').StaticMachine()
temporal=module('temporal408',HERE.parent/'kernel408/temporal-model.py').TemporalMachine()
sampling=module('sampling412',HERE.parent/'kernel412/tmc11-model.py').Tmc11Machine()
adrc=module('adrc409',HERE.parent/'kernel409/adrc-model.py').AdrcMachine()
inverse_model=module('inverse403',HERE.parent/'kernel403/ltm-model.py').LTM()
gamma=(P.parent/'kernel348/factory-gamma-private.bin').read_bytes()
green=[struct.unpack_from('<H',gamma,8+256+i*4)[0] for i in range(64)]
forward=[float(v) for v in green]+[float(green[-1]+struct.unpack_from('<h',gamma,8+256+63*4+2)[0])]
inverse=inverse_model.inverse(green)
axis=(P.parent/'kernel412/contrast-axis-private.bin').read_bytes()
gen_in=(P.parent/'kernel413/generation-valid-input-private.bin').read_bytes()
gen_out=(P.parent/'kernel413/generation-target-raw-private.bin').read_bytes()
cases=json.loads((P.parent/'kernel413/generation-cases-private.json').read_text())
profiles=json.loads((P.parent/'kernel351/mode-profiles-private.json').read_text())
tmc_profiles=json.loads((P.parent/'kernel412/mode-profiles-private.json').read_text())
def leaves(nodes):
    for node in nodes:
        if 'children' in node:yield from leaves(node['children'])
        else:yield node['data']
def flatten(data):
    out=[]
    for v in data.values():out.extend(v if isinstance(v,list) else [v])
    return out
def rounding(v):return int(math.copysign(math.floor(abs(v)+.5),v))
def unsigned(words,bits):
    out=bytearray()
    for w in struct.unpack('<'+str(len(words)//4)+'I',words):
        d=(w>>bits)&((1<<bits)-1)
        if d&(1<<(bits-1)):d-=1<<bits
        out+=struct.pack('<Hh',w&((1<<bits)-1),d)
    return out
def signed(words):
    out=bytearray()
    for w in struct.unpack('<'+str(len(words)//4)+'I',words):
        b=w&4095;d=(w>>12)&4095
        if b&2048:b-=4096
        if d&2048:d-=4096
        out+=struct.pack('<hh',b,d)
    return out
def pack_signed(values,count):
    raw=struct.pack('<2I65i',1 if count==64 else 2,count,*(list(values)+[0]*(65-len(values))))
    q=subprocess.run([str(P.parent/'kernel405/original-packers-private')],input=raw,capture_output=True)
    assert not q.returncode and len(q.stdout)==count*4,(q.returncode,len(q.stdout),count)
    return q.stdout
records=[];expected=[];rows=[]
for variant,contexts in profiles.items():
    # One ordinary Preview mode per physical supplier; this is a numeric fixture,
    # not a new binding of these modes to the reused main-camera forward table.
    context=next(c for c in contexts if c['usecase']=='Preview')
    root=context['modules']['ltm13_ipe'];r=root['reserve'];d=next(leaves(root['core']))
    tmc=next(c for c in tmc_profiles[variant] if c['usecase']=='Preview')['modules']['tmc11_sw']
    gi=next(i for i,c in enumerate(cases) if c['kind']=='factory-uniform' and any(b['variant']==variant and b['uid']==tmc['uid'] for b in c['source_bindings']))
    generated=gen_out[gi*8288:(gi+1)*8288]
    assert struct.unpack_from('<I',gen_in,gi*9408+184)[0]==1
    constants=struct.pack('<5f5I24i6i65i65fI',*[r[k] for k in ['c1','c2','c3','c4']],d['y_ratio_max'],
        *[r[k] for k in ['igamma_en','la_en','mask_filter_en','data_collect_en','img_process_en']],
        *r['wt_tab'],*r['mask_filter_kernel_tab'],*r['mask_rect_curve_tab'],*d['la_curve_tab'],r['lce_thd'])
    controls=[d[k] for k in ['ltm_strength','lce_strength','exp_atten_start','exp_atten_end','dark_boost','bright_suppress',
        'dark_range','bright_range','dark_max','bright_max','dark_gamma','bright_gamma']]+[180.,140.]
    curve=struct.pack('<113fI',*d['ltm_scale_tab'],*d['lce_scale_pos_tab'],*d['lce_scale_neg_tab'],*controls,r['ltm_scale_manual_curve_enable'])
    for use_adrc in [0,1]:
        control=struct.pack('<fII',float(use_adrc),0,0)
        history=bytes(404)
        cur,next_state,_=temporal.evaluate(struct.pack('<I',1)+curve+control+history)
        values=struct.unpack('<99f',cur);scale=[rounding(v) for v in values[:65]]
        positive=[max(-2048,min(2047,rounding(v))) for v in values[65:82]]
        negative=[max(-2048,min(2047,rounding(v))) for v in values[82:99]]
        constants_actual=static.evaluate(constants);fields=struct.unpack_from('<19I',constants_actual)
        program=struct.pack('<22I',*fields[5:8],0,*fields[:4],fields[18],fields[4],*fields[10:16],fields[17],fields[16],0,0,*fields[8:10])
        program+=struct.pack('<12H',*struct.unpack_from('<12I',constants_actual,76))
        program+=2*unsigned(constants_actual[380:636],12)
        if use_adrc:
            eq=struct.pack('<65f',*[float((w&16383)//4) for w in struct.unpack('<64I',inverse)],4095.)
            pchip=generated[:76];contrast=generated[76:88];hist=generated[4192:8288]
            normalized,mix=sampling.normalize(eq,pchip)
            gain=sampling.pchip(pchip,normalized);gain=sampling.contrast(normalized,gain,contrast,hist)
            assert struct.unpack_from('<f',gain)[0]>=1024
            data=eq+gain+struct.pack('<65f',*forward)+mix+struct.pack('<65i65h2x',*r['ltm_curve_tab'],*scale)
            actual,_=adrc.evaluate(data);blended=actual[528:918]
            curve_nodes=list(struct.unpack_from('<65i',blended));scale_nodes=list(struct.unpack_from('<65h',blended,260))
        else:curve_nodes=r['ltm_curve_tab'];scale_nodes=scale
        program+=unsigned(static.pack(curve_nodes),12)+signed(pack_signed(scale_nodes,64))
        program+=unsigned(constants_actual[124:380],12)
        program+=signed(pack_signed(positive,16))+signed(pack_signed(negative,16))
        program+=5*unsigned(inverse,14)
        assert len(program)==2800
        frame=constants+curve+control+struct.pack('<65i64H65f',*r['ltm_curve_tab'],*green,*forward)
        assert len(frame)==1800
        records.append(struct.pack('<I',use_adrc)+frame+history+generated+axis)
        expected.append(struct.pack('<I',1)+program+next_state)
        rows.append(dict(variant=variant,adrc=bool(use_adrc),passed=True))
valid=len(records)
invalid=[]
for offset,fmt,value in [(4,'f',math.nan),(4+1140,'f',math.nan),(0,'I',2),(4+1412,'H',1024),(4+1540,'f',math.nan)]:
    raw=bytearray(records[1]);struct.pack_into('<'+fmt,raw,offset,value);invalid.append(bytes(raw))
inputs=b''.join(records+invalid);gold=b''.join(expected)+len(invalid)*(struct.pack('<I',0)+bytes([0xa5])*3204)
(P/'frame-input-private.bin').write_bytes(inputs);(P/'frame-target-private.bin').write_bytes(gold)
names=['kernel422/frame-runner.cpp','kernel422/libipa/ltm13_frame.h','kernel422/libipa/ltm13_frame.cpp',
 'kernel422/libipa/ltm13_static.h','kernel422/libipa/ltm13_static.cpp','kernel352/libipa/ltm_inverse_gamma.h','kernel352/libipa/ltm_inverse_gamma.cpp',
 'kernel407/libipa/ltm_curves.h','kernel407/libipa/ltm_curves.cpp','kernel408/libipa/ltm_face_smoothing.h','kernel408/libipa/ltm_face_smoothing.cpp',
 'kernel409/libipa/ltm_adrc.h','kernel409/libipa/ltm_adrc.cpp','kernel412/libipa/tmc11_ltm.h','kernel412/libipa/tmc11_ltm.cpp','kernel413/libipa/tmc11_generation.h']
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss422-frame'
for n in names:
    out=work/n;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/n,out)
architectures=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror'];cpp=[n for n in names if n.endswith('.cpp')]
    if arch=='host':
        binary=P/'frame-host';cmd=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in cpp],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss422-frame/frame-arm64';cmd=['chroot',str(sdk),'g++',*flags,*['/private/camss422-frame/'+n for n in cpp],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(cmd,capture_output=True);(P/(arch+'-frame-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);(P/(arch+'-frame-output-private.bin')).write_bytes(q.stdout);assert not q.returncode,q.stderr.decode()
    assert len(q.stdout)==len(gold),(len(q.stdout),len(gold))
    diff=[i for i,(a,b) in enumerate(zip(q.stdout,gold)) if a!=b]
    architectures.append(dict(architecture=arch,cases=valid,invalid_cases=len(invalid),compared_bytes=len(gold),different_bytes=len(diff),passed=not diff))
    print(json.dumps(architectures[-1]),flush=True)
    if diff:print('first mismatch record,byte',diff[0]//3208,diff[0]%3208,flush=True)
report=dict(stage=422,cases=rows,invalid_cases=len(invalid),architectures=architectures,
    owned_proposed_pre_attenuation_pre_adrc_history=True,typed_kernel_payload_bytes=2800,all13_lut_banks_assembled=True,
    target_fragments_temporal_static_inverse_tmc11_sampling_and_adrc=True,prior_target_generation_outputs_reused=True,
    shared_main_forward_gamma_is_numeric_fixture_not_mode_binding=True,root_trigger_selection_not_in_this_assembler=True,
    hardware_and_runtime_history_commit_pending=True,phone_accessed=False,full_goal_complete=False,
    passed=all(r['passed'] for r in architectures))
path=HERE/'frame-validation.json'
if path.exists():
    i=1
    while (HERE/('frame-r'+str(i)+'-validation.json')).exists():i+=1
    (HERE/('frame-r'+str(i)+'-validation.json')).write_bytes(path.read_bytes())
path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
