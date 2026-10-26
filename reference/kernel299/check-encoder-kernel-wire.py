"""Validate the real libipa-produced wire image with actual kernel callbacks."""
from pathlib import Path
import hashlib,json,re,resource,subprocess
import host
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
report=json.loads((HERE/'ipa-encoder-validation.json').read_text());packet=P/'ipa-encoder-packet-private.bin'
assert hashlib.sha256(packet.read_bytes()).hexdigest()==report['packet_sha256']
old=(P.parent/'kernel298/blc-fixed-host-private.c').read_text();prefix=old[:old.index('static int submit(')]
pixel=(TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-pixel.c').read_text();body='\n'.join(l for l in pixel.splitlines() if not l.startswith('#include'));assert body in prefix
stats=(TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-stats.c').read_text()
validator=re.search(r'int vfe_175_bhist_validate\(.*?\n\}',stats,re.S)[0]
stub='static int vfe_175_bhist_validate(struct device*d,const struct v4l2_isp_block_header*b){(void)d;(void)b;return 0;}'
assert stub in prefix
defines='\n'.join(re.findall(r'^#define VFE_175_BHIST_MAX_.*$',stats,re.M));prefix=prefix.replace(stub,defines+'\n'+validator)
test=r'''
static int validate(void *p,size_t length){
 struct vb2_buffer vb={.payload=length};int ret=v4l2_isp_params_validate_buffer_size(NULL,&vb,sizeof(struct v4l2_isp_buffer)+CAMSS_PARAMS_IFE_MAX_PAYLOAD);
 return ret?ret:v4l2_isp_params_validate_buffer(NULL,&vb,p,vfe_175_params_info,6);
}
int main(int argc,char**argv){
 assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);unsigned char*p=malloc(56);assert(p);assert(fread(p,1,56,f)==56&&fgetc(f)==EOF);fclose(f);
 assert(!validate(p,56));struct vfe_device v={.base=(unsigned char*)bank};struct vfe_line pix={.is_pix=true,.owner=&v};memset(bank,0xa5,sizeof(bank));
 vfe_175_params_apply(&v,&pix,(struct v4l2_isp_buffer*)p);
 assert((bank[0x6b0/4]&0x3fff)==960&&(bank[0x6b0/4]>>15)==2048&&(bank[0x40/4]&0x800));
 assert((bank[0x6fc/4]&0xfff0fff)==(136U|(136U<<16))&&(bank[0x700/4]&0xfff)==136&&stats_calls==1);
 struct camss_params_wb_gain*wb=(void*)(p+8);wb->r_sub++;assert(validate(p,56)==-EINVAL);wb->r_sub--;
 struct camss_params_aec_bhist*h=(void*)(p+8+sizeof(*wb));h->width=3;assert(validate(p,56)==-EINVAL);h->width=1632;
 assert(validate(p,55)==-EINVAL);free(p);puts("REAL_LIBIPA_PACKET_ACCEPTED_BY_REAL_KERNEL_CALLBACKS");
}
'''
source=P/'encoder-kernel-wire-private.c';source.write_text(prefix+test);binary=P/'encoder-kernel-wire-private'
q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation','-D__EXPORTED_HEADERS__','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I'+str(TREE/'include/uapi'),str(source),'-o',str(binary)],capture_output=True)
(P/'encoder-kernel-wire-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary),str(packet)],capture_output=True);(P/'encoder-kernel-wire-run-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
out=dict(stage=299,aarch64_libipa_packet_accepted=True,actual_kernel_generic_parser_and_wb_bhist_validators=True,
 actual_pixel_register_callback=True,histogram_register_writes_not_tested_in_host_harness=True,
 resulting_bls_offset_u14=960,driver_blc_scale_q11=2048,resulting_wb_gain_q7=136,
 unequal_subtraction_odd_histogram_roi_and_short_packet_rejected=True,asan_ubsan_pass=True,
 packet_sha256=report['packet_sha256'],harness_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 kernel_source_sha256=hashlib.sha256(pixel.encode()).hexdigest(),no_uapi_or_kernel_change=True,
 full_hardware_pipeline_not_yet_integrated=True)
(HERE/'encoder-kernel-wire-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
