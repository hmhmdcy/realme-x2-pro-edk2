"""Compile actual paired-format functions with only V4L2 queue-busy stubs."""
from pathlib import Path
import hashlib,json,re,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;v=storage.mount.mounted_build().parent;k=v/'source354/drivers/media/platform/qcom/camss'
def function(text,name):
 m=re.search(r'(?:static )?(?:int|bool|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert m,name;return m[0]
ipe=(k/'camss-icp-a5-ipe.c').read_text();m2m=(k/'camss-icp-a5-m2m.c').read_text()
prefix='''#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <linux/videodev2.h>
typedef uint32_t u32;typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define SZ_32M (32U*1024*1024)
#define SZ_64M (64U*1024*1024)
#define V4L2_PIX_FMT_QCOM_NV12_PD10 v4l2_fourcc('Q','N','1','0')
#define min(a,b) ((a)<(b)?(a):(b))
#define max(a,b) ((a)>(b)?(a):(b))
#define min_t(type,a,b) min((type)(a),(type)(b))
#define max_t(type,a,b) max((type)(a),(type)(b))
#define clamp_val(x,a,b) min(max((x),(__typeof__(x))(a)),(__typeof__(x))(b))
#define ALIGN(x,a) (((x)+(__typeof__(x))((a)-1)) & ~(__typeof__(x))((a)-1))
struct camss_a5_nv12_layout {u32 width,height,stride,slice_height;bool uv_swap;};
struct camss_a5_pd10_layout {u32 width,height,stride,slice_height,bytes;};
struct ipe_context {struct v4l2_pix_format_mplane format;bool coarse;struct {void *m2m_ctx;}fh;};
struct file {struct ipe_context *ctx;};
static bool busy;
static struct ipe_context *file_context(struct file *file){return file->ctx;}
static void *v4l2_m2m_get_src_vq(void *ctx){(void)ctx;return NULL;}
static void *v4l2_m2m_get_dst_vq(void *ctx){(void)ctx;return NULL;}
static bool vb2_is_busy(void *queue){(void)queue;return busy;}
'''
for name in ['IPE_IMAGE_MAX','IPE_COARSE_MAX_BYTES']:prefix+=re.search(r'#define '+name+r'[^\n]*\n',m2m)[0]
code=prefix+function(ipe,'camss_a5_ipe_pd10_quarter')+'\n'+'\n'.join(function(m2m,n).replace('struct file *file,','struct file *file __attribute__((unused)),').replace('void *private,','void *private __attribute__((unused)),') for n in ['queue_format','try_format','set_format'])+'\n'+(HERE/'format-contract.c').read_text()
(P/'format-model.c').write_text(code);outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('format-contract-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'format-model.c'),'-o',str(binary)],capture_output=True);(P/(arch+'-format-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],capture_output=True);(P/(arch+'-format-run.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1]==b'FORMAT_CONTRACT negotiated=6 rejected=26 legacy=1 busy=1 result=0\n'
r=dict(stage=441,actual_production_function_bodies=True,unused_formal_parameters_annotated_only=True,queue_busy_stubs_not_hardware=True,paired_source_capture_dimension_stride_and_size_invariants=True,quarter_plane_bytes_and_stride_match_actual_helper=True,valid_sizes_with_padding_per_architecture=6,rejected_capture_mismatch_type_or_oversize_cases_per_architecture=26,busy_queue_preserves_context=True,legacy_single_plane_preserved=True,host_asan_ubsan=True,aarch64_static_qemu=True,phone_accessed=False,passed=True)
(HERE/'format-contract-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
