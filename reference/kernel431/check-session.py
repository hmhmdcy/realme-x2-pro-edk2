"""Execute the maintained session selector, including destroy failure preservation."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage431session',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);k=m.mounted_build().parent/'source354'
t=(k/'drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c').read_text();f=re.search(r'static int ensure_session\([^;]+?\n\{.*?^\}',t,re.S|re.M)[0]
code='''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <linux/videodev2.h>
struct layout {unsigned width,height,stride,slice_height;bool uv;};
struct camss_a5_ipe_io {struct layout input,output;unsigned output_port;};
struct camss_a5_pd10_layout {unsigned bytes;};
struct session {bool configured;unsigned handle;struct camss_a5_pd10_layout coarse;};
struct camss_a5_m2m {void *a5;};
struct ipe_context {struct camss_a5_m2m *dev;struct v4l2_pix_format_mplane format;struct session session;};
#define CAMSS_A5_IPE_RT 2
static unsigned calls[8],fail;
static int event(unsigned n){calls[n]++;return fail==n?-EIO:0;}
static int start_backend(struct camss_a5_m2m *d){(void)d;return event(1);}
static int camss_a5_ipe_create(void *a,struct session *s,unsigned type){(void)a;assert(type==2);int r=event(2);if(!r)s->handle=1;return r;}
static int camss_a5_ipe_destroy(void *a,struct session *s){(void)a;int r=event(3);if(!r)memset(s,0,sizeof(*s));return r;}
static int camss_a5_ipe_pd10_quarter(struct layout *l,struct camss_a5_pd10_layout *c){assert(l->width==640);int r=event(4);if(!r)c->bytes=46080;return r;}
static int camss_a5_ipe_configure_nv12_pd10(void *a,struct session *s,struct camss_a5_ipe_io *io,struct camss_a5_pd10_layout *c){(void)a;assert(io->output_port==8);int r=event(5);if(!r){s->configured=true;s->coarse=*c;}return r;}
static int camss_a5_ipe_configure_nv12(void *a,struct session *s,struct camss_a5_ipe_io *io){(void)a;assert(io->input.width==io->output.width);int r=event(6);if(!r){s->configured=true;s->coarse.bytes=0;}return r;}
'''+f+'''
int main(void){
 struct camss_a5_m2m dev={};struct ipe_context ctx={.dev=&dev,.format={.width=640,.height=480,.pixelformat=V4L2_PIX_FMT_NV12,.plane_fmt={{.bytesperline=640}}}};
 assert(!ensure_session(&ctx,false) && ctx.session.configured && !ctx.session.coarse.bytes);
 assert(!ensure_session(&ctx,true) && ctx.session.coarse.bytes==46080 && calls[3]==1);
 unsigned created=calls[2];assert(!ensure_session(&ctx,true)&&calls[2]==created&&calls[3]==1);
 struct session saved=ctx.session;fail=3;assert(ensure_session(&ctx,false)==-EIO&&!memcmp(&saved,&ctx.session,sizeof(saved))&&calls[2]==created);
 fail=1;unsigned destroyed=calls[3];assert(ensure_session(&ctx,false)==-EIO&&calls[3]==destroyed&&!memcmp(&saved,&ctx.session,sizeof(saved)));
 fail=0;assert(!ensure_session(&ctx,false)&&!ctx.session.coarse.bytes);
 assert(!ensure_session(&ctx,true)&&ctx.session.coarse.bytes==46080);
 puts("SESSION_TRANSITION cases=7 passed=1");return 0;}
'''
(P/'session-test.c').write_text(code);outputs=[]
for arch,cc,flags,launcher in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('arm64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 out=P/('session-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'session-test.c'),'-o',str(out)],capture_output=True);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launcher,str(out)],capture_output=True);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1]
r=dict(stage=431,actual_maintained_session_selector_executed=True,host_asan_ubsan=True,arm64_qemu=True,werror=True,cases=7,bootstrap_bypass_dc_reuse_and_return_transitions=True,destroy_failure_preserves_session_and_suppresses_create=True,backend_failure_preserves_session=True,passed=True)
(HERE/'session-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
