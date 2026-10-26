"""Fix the FULL descriptor guard that still counted a zero-DMA params node as an image."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'kernel293';OUT.mkdir(exist_ok=False)
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel');PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel293');PRIVATE.mkdir(mode=0o700)
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='86c7b9df030382efa82d87bc49370b3ad3a07cf3' and not git('status','--porcelain')
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-params293'],check=True,capture_output=True)
path='drivers/media/platform/qcom/camss/camss-vfe-175-output.c';p=TREE/path;s=p.read_text();old=s
s=s.replace('output->comp_group != 0 || output->line->num_outputs != 1 ||','output->comp_group != 0 ||')
needle='\tif (pix->pixelformat != V4L2_PIX_FMT_NV12'
assert needle in s
s=s.replace(needle,'''	/* Parameters have no write masters and do not add a second image. */
	if (output->line->num_outputs == 2) {
		const struct vfe_output *params = &output->line->output[1];

		if (params->pad != MSM_VFE_PAD_SINK_PARAMS || params->wm_num)
			return -EINVAL;
	} else if (output->line->num_outputs != 1) {
		return -EINVAL;
	}

'''+needle)
assert s!=old;p.write_text(s)
patch=subprocess.check_output(['git','-C',str(TREE),'diff']);(OUT/'full-with-params.patch').write_bytes(patch)
q=subprocess.run([str(TREE/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True);(PRIVATE/'checkpatch-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stdout.decode()
def functions(src):
 return '\n'.join(re.search(re.escape('int '+name)+r'\(.*?\n\}',src,re.S)[0] for name in ['vfe_175_validate_output','vfe_175_validate_buffer'])
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <limits.h>
#include <linux/videodev2.h>
typedef uint32_t u32;typedef uint64_t u64;
#define U16_MAX UINT16_MAX
#define U32_MAX UINT32_MAX
#define IS_ALIGNED(x,a) (!((x)&((a)-1)))
#define MSM_VFE_PAD_SRC 1
#define MSM_VFE_PAD_SINK_PARAMS 5
#define VFE_175_FULL_Y 3
#define VFE_175_FULL_C 4
#define VFE_175_FULL_MAX_WIDTH 4096
#define VFE_175_FULL_MAX_HEIGHT 4096
struct vfe_line;
struct vfe_output {struct vfe_line *line;unsigned int pad,wm_num,comp_group;struct{unsigned int bus_client,plane;}wm[2];struct{struct v4l2_format active_fmt;}video_out;};
struct vfe_line{bool is_pix;unsigned int num_outputs;struct vfe_output output[4];};
struct camss_buffer{u64 addr[2];};
'''
main=r'''
int main(void){
 struct vfe_line line={.is_pix=true,.num_outputs=1};struct vfe_output *o=&line.output[0];
 o->line=&line;o->pad=1;o->wm_num=2;o->comp_group=0;o->wm[0].bus_client=3;o->wm[1].bus_client=4;o->wm[1].plane=1;
 struct v4l2_pix_format_mplane *p=&o->video_out.active_fmt.fmt.pix_mp;
 p->pixelformat=V4L2_PIX_FMT_NV12;p->num_planes=1;p->width=320;p->height=240;p->plane_fmt[0].bytesperline=320;p->plane_fmt[0].sizeimage=115200;
 struct camss_buffer b={.addr={0x10000,0x10000+76800}};
 assert(!vfe_175_validate_output(o)&&!vfe_175_validate_buffer(o,&b));
 line.num_outputs=2;line.output[1].pad=5;assert(!vfe_175_validate_output(o)&&!vfe_175_validate_buffer(o,&b));
 for(unsigned n=0;n<8;n++){line.num_outputs=n;if(n!=1&&n!=2)assert(vfe_175_validate_output(o)==-EINVAL);}line.num_outputs=2;
 for(unsigned pad=0;pad<8;pad++)for(unsigned wm=0;wm<4;wm++){line.output[1].pad=pad;line.output[1].wm_num=wm;assert((vfe_175_validate_output(o)==0)==(pad==5&&wm==0));}
 line.output[1].pad=5;line.output[1].wm_num=0;
 o->wm[0].bus_client=2;assert(vfe_175_validate_buffer(o,&b)==-EINVAL);o->wm[0].bus_client=3;
 o->wm[1].plane=0;assert(vfe_175_validate_output(o)==-EINVAL);o->wm[1].plane=1;
 b.addr[1]++;assert(vfe_175_validate_buffer(o,&b)==-EINVAL);b.addr[1]--;
 b.addr[0]=UINT32_MAX-15;b.addr[1]=b.addr[0]+76800;assert(vfe_175_validate_buffer(o,&b)==-ERANGE);
 return 0;
}
'''
flags=['gcc','-std=gnu11','-O1','-g','-Wall','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer']
for tag,src in [('parent',old),('fixed',s)]:
 test=PRIVATE/(tag+'-full-params-test-private.c');test.write_text(prefix+functions(src)+main);binary=test.with_suffix('')
 q=subprocess.run(flags+[str(test),'-o',str(binary)],capture_output=True);assert q.returncode==0,q.stderr.decode()
 q=subprocess.run([str(binary)],capture_output=True);(PRIVATE/(tag+'-test-private.log')).write_bytes(q.stdout+q.stderr)
 if tag=='parent':assert q.returncode!=0
 else:assert q.returncode==0,q.stderr.decode()
report=dict(stage=293,parent=git('rev-parse','HEAD'),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),actual_functions_tested=True,asan_ubsan=True,parent_rejects_valid_full_plus_params=True,full_alone_and_full_with_zero_dma_params_pass=True,extra_dma_or_unknown_aux_rejected=True,existing_dma_bounds_and_client_checks_retained=True,device_not_yet_changed=True)
(OUT/'full-params-host-validation.json').write_text(json.dumps(report,indent=2)+'\n')
msg=PRIVATE/'commit-message-private.txt';msg.write_text('media: qcom: camss: allow zero-DMA parameters with VFE175 FULL\n\nThe FULL buffer validator still required a line with exactly one output. A typed parameters node is a zero-DMA auxiliary output, so registering it made every FULL image QBUF fail with EINVAL. Accept the existing single-image descriptor with one optional parameters output while rejecting any extra DMA output or unsupported pad. Keep all FULL client, format and DMA bounds checks.\n')
subprocess.run(['git','-C',str(TREE),'add','--',path],check=True);subprocess.run(['git','-C',str(TREE),'commit','-F',str(msg)],check=True,capture_output=True)
report.update(commit=git('rev-parse','HEAD'),source_clean=not git('status','--porcelain'),branch=git('branch','--show-current'),checkpatch_errors=0,checkpatch_warnings=0,pushed=False)
(OUT/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
