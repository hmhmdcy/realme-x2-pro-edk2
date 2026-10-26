"""Verify both packers at int16 boundaries and rerun saved native math cases."""
from pathlib import Path
import hashlib,json,math,random,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
adrc=json.loads((HERE/'adrc-validation.json').read_text());assert adrc['passed']
count=adrc['valid_cases'];raw=(P/'host-actual-private.bin').read_bytes()
records=[raw[i*918+528:(i+1)*918]+bytes(2) for i in range(count)]
labels=['adrc']*count
for a,b in [(-32768,2047),(-32768,0),(-32768,1),(-32767,2047),(-30000,2047),(-2048,2047),(32767,-32768),(2047,-32768)]:
    for curve in [[0]*65,[4095 if i%2 else 0 for i in range(65)],[(1<<31)-1 if i%2 else 4096 for i in range(65)]]:
        scale=[a if i%2 else b for i in range(65)]
        records.append(struct.pack('<65i65h2x',*curve,*scale));labels.append('signed-boundary')
rng=random.Random(0x409)
for i in range(128):
    records.append(struct.pack('<65i65h2x',*[rng.randrange(20000) for _ in range(65)],*[rng.randrange(-32768,32768) for _ in range(65)]));labels.append('random-signed-nodes')
valid_count=len(records)
packer=P.parent/'kernel405/original-packers-private'
source_input=b''.join(struct.pack('<2I65i',0,64,*struct.unpack_from('<65i',r))+
                      struct.pack('<2I65i',1,64,*struct.unpack_from('<65h',r,260)) for r in records)
q=subprocess.run([str(packer)],input=source_input,capture_output=True);assert not q.returncode,q.stderr.decode()
gold=q.stdout;assert len(gold)==valid_count*512
expected=b''.join(struct.pack('<I',1)+gold[i*512+256:(i+1)*512]+struct.pack('<I',1)+gold[i*512:(i+1)*512] for i in range(valid_count))
for at in [0,64]:
    r=bytearray(records[0]);struct.pack_into('<i',r,at*4,-1);records.append(bytes(r))
    expected+=struct.pack('<I',1)+gold[256:512]+struct.pack('<I',0)+bytes([0xa5])*512
inputs=b''.join(records)
(P/'packing-input-private.bin').write_bytes(inputs);(P/'packing-expected-private.bin').write_bytes(expected)
(P/'packing-source-luts-private.bin').write_bytes(gold)
(P/'packing-labels-private.json').write_text(json.dumps(labels,indent=2)+'\n')
old=P.parent/'kernel407'
legacy_input=(old/'curve-input-private.bin').read_bytes()
for at in [0,64,65,81,82,98,*range(99,113)]:
    for value in [math.nan,math.inf,-math.inf,2097152.0]:
        r=bytearray(legacy_input[:456]);struct.pack_into('<f',r,at*4,value);legacy_input+=r
r=bytearray(legacy_input[:456]);struct.pack_into('<I',r,452,2);legacy_input+=r
legacy_expected=(old/'curves-host-output-private.bin').read_bytes()
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss409-packing'
names=['kernel409/packing-runner.cpp','kernel409/adrc-runner.cpp','kernel409/libipa/ltm_adrc.cpp','kernel409/libipa/ltm_adrc.h',
       'kernel407/curve-runner.cpp','kernel407/libipa/ltm_curves.cpp','kernel407/libipa/ltm_curves.h']
for name in names:
    target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,target)
rows=[]
for arch in ['host','aarch64']:
    for kind in ['packing','adrc','legacy']:
        sources={'packing':['kernel409/packing-runner.cpp','kernel409/libipa/ltm_adrc.cpp','kernel407/libipa/ltm_curves.cpp'],
                 'adrc':['kernel409/adrc-runner.cpp','kernel409/libipa/ltm_adrc.cpp'],
                 'legacy':['kernel407/curve-runner.cpp','kernel407/libipa/ltm_curves.cpp']}[kind]
        options=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
        if arch=='host':
            binary=P/(kind+'-final-host');command=['g++',*options,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/r) for r in sources],'-o',str(binary)];launch=[str(binary)]
        else:
            binary='/private/camss409-packing/'+kind+'-aarch64';command=['chroot',str(sdk),'g++',*options,*['/private/camss409-packing/'+r for r in sources],'-o',binary];launch=['chroot',str(sdk),binary]
        q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
        data,wanted={'packing':(inputs,expected),'adrc':((P/'adrc-input-private.bin').read_bytes(),(P/'adrc-expected-private.bin').read_bytes()),'legacy':(legacy_input,legacy_expected)}[kind]
        q=subprocess.run(launch,input=data,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
        assert len(q.stdout)==len(wanted)
        (P/(kind+'-'+arch+'-final-private.bin')).write_bytes(q.stdout)
        differences=sum(a!=b for a,b in zip(q.stdout,wanted))
        rows.append(dict(architecture=arch,scope=kind,compared_bytes=len(wanted),different_bytes=differences,passed=not differences))
        print(json.dumps(rows[-1]),flush=True)
result=dict(stage=409,valid_cases=valid_count,invalid_unsigned_curve_cases=2,adrc_cases=count,
            extra_boundary_cases=24,extra_random_cases=128,rows=rows,
            unsigned_and_signed_original_source_packers_used=True,
            positive_signed_delta_at_least32768_sign_rule_covered=True,
            public_lut_api_has_no_commands_or_device_addresses=True,
            input_and_invalid_output_unchanged=True,
            current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in names],
            phone_accessed=False,passed=all(r['passed'] for r in rows))
path=HERE/'packing-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'packing-r1-validation.json').exists():
    (HERE/'packing-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
assert result['passed']
