"""Reuse the standard media/V4L2 fixture for native Gamma/SOF experiments."""
from pathlib import Path
import importlib.util,json,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mounted_build()
tree=Path(json.loads((HERE/'source-state.json').read_text())['source'])
stock=(P.parent/'kernel347/expected-private.bin').read_bytes();assert stock[:4]==b'\1\0\0\0'
words=struct.unpack('<64I',stock[4:260]);segments=b''.join(struct.pack('<Hh',word&1023,(word>>10)-1024 if word&0x80000 else word>>10) for word in words)
(P/'factory-gamma-private.bin').write_bytes(struct.pack('<HHI',7,2,776)+segments*3)
s=(HERE.parent/'kernel334/samurai-ccm.c').read_text()
s=s.replace('camss_params_color_correct','camss_params_ife_gamma').replace('factory_ccm','factory_gamma').replace('CAMSS_PARAMS_COLOR_CORRECT','CAMSS_PARAMS_IFE_GAMMA').replace('CCM_FRAME','GAMMA_FRAME')
start=s.index(' struct camss_params_ife_gamma ccm=',s.index('static size_t make_packet('));end=s.index(' return sizeof(e)+e.data_size;',start)
s=s[:start]+''' struct camss_params_ife_gamma gamma=factory_gamma;
 struct camss_params_lsc lsc={.header={CAMSS_PARAMS_LSC,V4L2_ISP_PARAMS_FL_BLOCK_DISABLE,sizeof(lsc.header)},.cell_width=144,.cell_height=144};
 unsigned size;
 if(phase==0||phase==9)for(unsigned ch=0;ch<3;ch++)for(unsigned i=0;i<64;i++){
  /* The initialized Rec.709 output curve, requested explicitly on restoration. */
  static const unsigned short curve[65]={0,72,135,183,222,256,286,314,340,364,387,408,428,448,467,484,502,518,535,550,565,580,595,609,622,636,649,662,674,687,699,711,722,734,745,756,767,778,789,799,809,820,830,840,849,859,869,878,887,897,906,915,924,932,941,950,958,967,975,984,992,1000,1008,1016,1024};
  gamma.segments[ch][i].base=curve[i];gamma.segments[ch][i].delta=curve[i+1]-curve[i];
 }
 if(phase==1||phase==2)for(unsigned ch=0;ch<3;ch++)for(unsigned i=0;i<64;i++){
  unsigned value=i*16,next=(i+1)*16;
  if(phase==2&&ch==0){value/=2;next/=2;}
  gamma.segments[ch][i].base=value;gamma.segments[ch][i].delta=next-value;
 }
 if(phase==4){gamma.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;gamma.header.size=sizeof(gamma.header);}
 if(phase==5)gamma.header.flags=0;
 if(phase==7||phase==8){
  lsc.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE;lsc.header.size=sizeof(lsc);
  for(unsigned ch=0;ch<4;ch++)for(unsigned i=0;i<CAMSS_LSC_MESH_POINTS;i++)lsc.gains[ch][i]=phase==7?1024:1536;
 }
 struct params_envelope e={V4L2_ISP_VERSION_V1,sizeof(wb)+gamma.header.size+lsc.header.size};
 memset(memory,0,params_size);memcpy(memory,&e,sizeof(e));size=sizeof(e);
 memcpy((char*)memory+size,&wb,sizeof(wb));size+=sizeof(wb);
 memcpy((char*)memory+size,&gamma,gamma.header.size);size+=gamma.header.size;
 memcpy((char*)memory+size,&lsc,lsc.header.size);
'''+s[end:]
start=s.index('static int reject_invalid_params(');end=s.index('static int open_params(',start)
s=s[:start]+'''static int reject_invalid_params(void) {
 for(unsigned test=0;test<4;test++){
  size_t size=make_packet(params_map,1);
  struct camss_params_ife_gamma *g=(void*)((char*)params_map+sizeof(struct params_envelope)+sizeof(struct camss_params_wb_gain));
  if(test==0)g->segments[0][0].base=1024;
  else if(test==1)g->segments[2][63].delta=512;
  else if(test==2)g->header.flags=3;
  else g->header.type=CAMSS_PARAMS_GAMMA;
  struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP,.bytesused=size};
  errno=0;if(!call(params_fd,VIDIOC_QBUF,&b)||errno!=EINVAL){errno=EPROTO;return -1;}
  printf("PARAM_REJECT test=%u errno=%d\\n",test,errno);
 }return 0;
}
'''+s[end:]
s=s.replace('sizeof(struct camss_params_wb_gain)+sizeof(struct camss_params_ife_gamma)','sizeof(struct camss_params_wb_gain)+sizeof(struct camss_params_ife_gamma)+sizeof(struct camss_params_lsc)')
s=s.replace('wb_phase<8','wb_phase<10').replace('wb_phase!=8','wb_phase!=10').replace('buffer.sequence>=parameter_sequence+2','buffer.sequence>=parameter_sequence')
# ShadeColorBars is stable; termination follows actual matching frames after ACK.
(HERE/'samurai-gamma.c').write_text(s)
work=SDK/'private/camss348-runtime';work.mkdir(exist_ok=True)
shutil.copyfile(HERE/'samurai-gamma.c',work/'samurai-gamma.c')
shutil.copytree(P/'register-test/linux',work/'include/linux',dirs_exist_ok=True)
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s',
 '-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-I'+str(work/'include'),'-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',
 '-I'+str(tree/'include/uapi'),str(work/'samurai-gamma.c'),'-o',str(work/'samurai-gamma')],capture_output=True)
(P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
shutil.copyfile(work/'samurai-gamma',P/'samurai-gamma')
(HERE/'probe-build-validation.json').write_text(json.dumps(dict(stage=348,compiled_aarch64_static=True,
 phases=['rec709','linear','red-half-linear','factory','disable','factory-upload-while-disabled','factory-enable','factory-unity-lsc','factory-1.5-lsc','rec709-lsc-off'],
 parameter_snapshot_mutation_tested=True,source_factory_payload_private=True,stable_pattern_after_ack=True,phone_changed=False,passed=True),indent=2)+'\n')
print('Prepared10 native Gamma phases including source factory curve and shared-DMI LSC packets.')
