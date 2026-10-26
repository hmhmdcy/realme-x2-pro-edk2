"""Build a four-job FULL-only control using the existing formal media-request ABI."""
from pathlib import Path
import ast,hashlib,importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
text=(HERE.parent/'kernel429/pd10-ipe.c').read_text()
text=text.replace('/* Bounded real PD10 replay through the ordinary media-request queues. */','/* Repeated FULL input with LTM disabled and with single-pass IP enabled. */')
text=text.replace('type==out_type?V4L2_PIX_FMT_QCOM_NV12_PD10:V4L2_PIX_FMT_NV12','V4L2_PIX_FMT_NV12').replace('type==out_type?2:1','1')
text=text.replace('\n\tif(type==out_type)assert(f.fmt.pix_mp.plane_fmt[1].sizeimage==46080 && f.fmt.pix_mp.plane_fmt[1].bytesperline==768);','')
text=text.replace('\n\tif(type==out_type)assert(planes[1].bytesused==46080);','')
a=text.index('static unsigned scratch(');z=text.index('int main(',a);text=text[:a]+text[z:]
text=text.replace('\n\tunsigned char *data=malloc(0x40000+16);assert(data);','')
text=text.replace('\n\t\tstruct memory input[2],output[1];','\n\t\tparams.ltm.iq.data_collection=0;\n\t\tif(mode<2)params.flags&=~QCOM_IPE_A5_LTM;else params.flags|=QCOM_IPE_A5_LTM;\n\t\tstruct memory input[1],output[1];')
a=text.index('\n\t\tread_exact(directory,"pd10-private.bin"');z=text.index('\n\t\tint request=',a)
text=text[:a]+'\n\t\tuint64_t full_hash=hash(input[0].p,460800);'+text[z:]
text=text.replace(' && hash(input[1].p,46080)==coarse_hash','')
a=text.index('\n\t\tunsigned bytes=scratch(');z=text.index('\n\t\ttype=out_type;call(fd,VIDIOC_STREAMOFF',a)
text=text[:a]+'''\n\t\tsave(directory,mode,"output-private",output[0].p,460800);
\t\tprintf("{\\\"mode\\\":%u,\\\"ltm_enabled\\\":%s,\\\"full_hash\\\":\\\"%016llx\\\",\\\"output_hash\\\":\\\"%016llx\\\",\\\"passed\\\":true}\\n",mode,mode<2?"false":"true",(unsigned long long)full_hash,(unsigned long long)hash(output[0].p,460800));fflush(stdout);'''+text[z:]
text=text.replace('for(unsigned i=0;i<2;i++)','for(unsigned i=0;i<1;i++)').replace('free(data);puts("PD10_IPE_RESULT result=0 frames=4")','puts("CONTROL_RESULT result=0 frames=4")')
assert 'input[1].p' not in text and 'scratch(' not in text and 'coarse_hash' not in text
(HERE/'control-ipe.c').write_text(text)
s=importlib.util.spec_from_file_location('storage430',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
k=storage.mounted_build().parent/'source354';inc=P/'include/linux';inc.mkdir(parents=True,exist_ok=True);shutil.copyfile(k/'include/uapi/linux/qcom-ipe-a5.h',inc/'qcom-ipe-a5.h')
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-I'+str(inc.parent),str(HERE/'control-ipe.c'),'-o',str(P/'control-ipe')],capture_output=True)
(P/'control-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
for n in ['full-private.bin','parameters-private.bin']:shutil.copyfile(P.parent/'kernel429'/n,P/n)
r=dict(stage=430,formal_6008_byte_abi=True,static_arm64_werror=True,source_sha256=hashlib.sha256(text.encode()).hexdigest(),binary_sha256=hashlib.sha256((P/'control-ipe').read_bytes()).hexdigest(),
 modes=['LTM disabled','repeat LTM disabled','single-pass IP, DC disabled','repeat single-pass IP, DC disabled'],no_module_change_required=True,passed=True)
(HERE/'control-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
