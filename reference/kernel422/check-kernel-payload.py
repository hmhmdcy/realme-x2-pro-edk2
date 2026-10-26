"""Verify assembled typed frames with the maintained native kernel codec."""
from pathlib import Path
import ctypes,importlib.util,json,shutil,struct,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel422')
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
kernel=storage.mounted_build().parent/'source354';source=kernel/'drivers/media/platform/qcom/camss'
model=P/'codec422';model.mkdir(exist_ok=True)
shutil.copytree(P.parent/'kernel405/include',model/'include',dirs_exist_ok=True)
shutil.copyfile(P.parent/'kernel405/bypass.c',model/'bypass.c')
shutil.copyfile(source/'camss-icp-a5-colour.c',model/'colour.c')
shutil.copyfile(source/'camss-icp-a5-colour.h',model/'include/camss-icp-a5-colour.h')
shutil.copyfile(kernel/'include/uapi/linux/qcom-ipe-a5.h',model/'include/linux/qcom-ipe-a5.h')
with (model/'include/linux/types.h').open('a') as f:f.write('\n#include_next <linux/types.h>\n')
with (model/'include/linux/kernel.h').open('a') as f:f.write('\n#include <stddef.h>\n#define static_assert(...) _Static_assert(__VA_ARGS__, "layout")\n')
with (model/'include/linux/string.h').open('a') as f:f.write('''
static inline void *memchr_inv(const void *p,int c,size_t n) {
 const unsigned char *b=p;for(size_t i=0;i<n;++i)if(b[i]!=(unsigned char)c)return (void *)(b+i);return 0;
}
''')
(model/'include/linux/export.h').write_text('#define EXPORT_SYMBOL_GPL(name)\n')
q=subprocess.run(['gcc','-shared','-fPIC','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(model/'include'),str(model/'colour.c'),str(model/'bypass.c'),'-o',str(P/'current-colour-codec.so')],capture_output=True)
(P/'codec-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
library=ctypes.CDLL(str(P/'current-colour-codec.so'))
encode=library.camss_a5_ipe_encode_ltm_iq
encode.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];encode.restype=ctypes.c_int
validate=library.camss_a5_ipe_frame_params_check;validate.argtypes=[ctypes.c_void_p];validate.restype=ctypes.c_int
gold=(P/'frame-target-private.bin').read_bytes();cases=0
for start in range(0,len(gold),3208):
    if struct.unpack_from('<I',gold,start)[0]!=1:continue
    payload=gold[start+4:start+2804];assert len(payload)==2800
    output=ctypes.create_string_buffer(bytes([0xa7])*9008);request=ctypes.create_string_buffer(payload)
    assert encode(output,9008,0x07802000,None,None,request)==0
    assert output.raw[2096:2188]==struct.pack('<I',1)+payload[:88]
    tables=struct.pack('<12I',*struct.unpack_from('<12H',payload,88))
    for offset,count,bits,signed in [(112,64,12,False),(368,64,12,False),(624,64,12,False),
        (880,64,12,True),(1136,64,12,False),(1392,16,12,True),(1456,16,12,True),
        *[(1520+bank*256,64,14,False) for bank in range(5)]]:
        for i in range(count):
            base,delta=struct.unpack_from('<'+('h' if signed else 'H')+'h',payload,offset+i*4)
            mask=(1<<bits)-1;tables+=struct.pack('<I',(base&mask)|((delta&mask)<<bits))
    assert len(tables)==2736 and output.raw[6208:8944]==tables
    assert output.raw[8944:9008]==bytes([0xa7])*64 and request.raw[:2800]==payload
    packet=struct.pack('<8I',1,6008,2,0,0,0,0,0)+bytes(104+3072)+payload
    assert len(packet)==6008 and validate(ctypes.create_string_buffer(packet))==0
    cases+=1
r=dict(stage=422,valid_frame_payloads=cases,maintained_native_codec_matches_preserved_source=True,
    typed_payload_bytes=2800,iq_bytes_per_case=92,all13_lut_bytes_per_case=2736,media_request_6008_byte_validator_accepts=True,
    actual_native_codec_iq_and_all_tables_exact=True,caller_input_and_output_tail_preserved=True,
    colour_gamma_physical_domain_not_claimed=True,new_hardware_frames=0,passed=cases==8)
(HERE/'kernel-payload-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
