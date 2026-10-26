"""Exercise the actual kernel typed validator, including ABI and rejection."""
from pathlib import Path
import importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';camss=source/'drivers/media/platform/qcom/camss'
inc=P/'include';shutil.copytree(P.parent/'kernel405/include',inc,dirs_exist_ok=True)
for n in ['camss-icp-a5-colour.h']:(inc/n).write_bytes((camss/n).read_bytes())
(inc/'linux/qcom-ipe-a5.h').write_bytes((HERE/'qcom-ipe-a5.h').read_bytes())
(inc/'linux/types.h').write_text('#include_next <linux/types.h>\ntypedef __u8 u8;typedef __u16 u16;typedef __s16 s16;typedef __u32 u32;typedef __s32 s32;typedef __u64 u64;\n')
(inc/'linux/kernel.h').write_text('#include <assert.h>\n#include <stddef.h>\n#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))\n')
(inc/'linux/export.h').write_text('#define EXPORT_SYMBOL_GPL(x)\n')
(inc/'linux/string.h').write_text('#include <string.h>\nstatic inline void *memchr_inv(const void *p,int c,size_t n){const unsigned char *s=p;for(size_t i=0;i<n;i++)if(s[i]!=(unsigned char)c)return (void *)(s+i);return 0;}\n')
(P/'colour.c').write_bytes((camss/'camss-icp-a5-colour.c').read_bytes())
model=HERE/'params-model.c'
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-strict-aliasing','-no-pie','-I'+str(inc),str(P/'colour.c'),str(model),'-o',str(P/'params-model')],capture_output=True)
(P/'params-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
q=subprocess.run([str(P/'params-model')],capture_output=True);(P/'params-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
r=dict(stage=417,actual_candidate_colour_validator=True,asan_ubsan=True,abi_bytes=6008,**json.loads(q.stdout),hardware_not_claimed=True)
(HERE/'params-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
