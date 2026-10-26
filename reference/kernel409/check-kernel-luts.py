"""Verify native typed LUT pages and regress shared temporal quantization."""
from pathlib import Path
import ctypes,importlib.util,json,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
validation=json.loads((HERE/'packing-validation.json').read_text());assert validation['passed']
count=validation['valid_cases']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';directory=source/'drivers/media/platform/qcom/camss'
model=P.parent/'kernel405'
assert (model/'colour.c').read_bytes()==(directory/'camss-icp-a5-colour.c').read_bytes()
assert (model/'include/camss-icp-a5-colour.h').read_bytes()==(directory/'camss-icp-a5-colour.h').read_bytes()
q=subprocess.run(['gcc','-shared','-fPIC','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(model/'include'),str(model/'colour.c'),str(model/'bypass.c'),'-o',str(P/'current-colour-codec.so')],capture_output=True)
assert not q.returncode,q.stderr.decode()
lib=ctypes.CDLL(str(P/'current-colour-codec.so'));encode=lib.camss_a5_ipe_encode_ltm_iq
encode.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];encode.restype=ctypes.c_int
raw=(P/'packing-host-final-private.bin').read_bytes();gold=(P/'packing-source-luts-private.bin').read_bytes()
different=0
for i in range(count):
    native=raw[i*776+264:(i+1)*776];assert native==gold[i*512:(i+1)*512]
    typed=bytearray(2800);struct.pack_into('<I',typed,84,1)
    for family,at in [(0,624),(1,880)]:
        for j,word in enumerate(struct.unpack_from('<64I',native,family*256)):
            base=word&4095;delta=(word>>12)&4095
            if delta&2048:delta-=4096
            if family:
                if base&2048:base-=4096
                struct.pack_into('<hh',typed,at+j*4,base,delta)
            else:struct.pack_into('<Hh',typed,at+j*4,base,delta)
    request=ctypes.create_string_buffer(bytes(typed));output=ctypes.create_string_buffer(bytes([0xa7])*9008)
    assert not encode(output,9008,0x7802000,None,None,request)
    assert request.raw[:2800]==typed and output.raw[8944:9008]==bytes([0xa7])*64
    different+=sum(a!=b for a,b in zip(output.raw[6768:7280],native))
assert not different

# The shared407 encoder also serves408: test that caller with current code.
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss409-packing'
names=['kernel408/temporal-runner.cpp','kernel408/libipa/ltm_face_smoothing.cpp','kernel408/libipa/ltm_face_smoothing.h',
       'kernel407/libipa/ltm_curves.cpp','kernel407/libipa/ltm_curves.h']
for name in names:
    target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,target)
rows=[];inputs=(P.parent/'kernel408/temporal-input-private.bin').read_bytes();expected=(P.parent/'kernel408/temporal-expected-private.bin').read_bytes()
for arch in ['host','aarch64']:
    rels=['kernel408/temporal-runner.cpp','kernel408/libipa/ltm_face_smoothing.cpp','kernel407/libipa/ltm_curves.cpp']
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
    if arch=='host':
        binary=P/'temporal-current-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in rels],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss409-packing/temporal-current-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss409-packing/'+n for n in rels],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    assert q.stdout==expected
    rows.append(dict(architecture=arch,records=3978,compared_bytes=len(expected),different_bytes=0,passed=True))
    print(json.dumps(rows[-1]),flush=True)
first=(P/'packing-host-r1-private.bin').read_bytes();wanted=(P/'packing-expected-private.bin').read_bytes();n=len(first)//776
old_diff=sum(a!=b for i in range(n) for a,b in zip(first[i*776+4:i*776+260],wanted[i*776+4:i*776+260]))
new_diff=sum(a!=b for i in range(n) for a,b in zip(first[i*776+264:(i+1)*776],wanted[i*776+264:(i+1)*776]))
assert old_diff==698 and new_diff==0
report=dict(stage=409,native_typed_cases=count,compared_lut_bytes=count*512,different_bytes=different,
             source_commit=json.loads((HERE/'source-state.json').read_text())['commit'],
             actual_maintained_colour_encoder_source_compiled=True,
             host_kernel_codec_only_no_new_hardware_submission=True,
             quantized_source_nodes_to_typed_curve_and_scale_to_native_lut=True,
             typed_input_and_output_tail_unchanged=True,
             remaining_iq_and_luts_zero_not_claimed_factory_pipeline=True,
             temporal408_regression=rows,initial_legacy_scale_different_bytes=old_diff,
             initial_new_adrc_tables_different_bytes=new_diff,
             phone_accessed=False,passed=True)
(HERE/'kernel-luts-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
