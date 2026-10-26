"""Derive an ambient-light independent LSC exercise from the existing MC tool."""
from pathlib import Path
import json, shutil, subprocess
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel299/samurai-factory-bls.c').read_text()
s=s.replace('static bool hold_statistics;static unsigned held_statistics[3],held_count;\n','')
a=s.index('static int stats_fd=');b=s.index('struct format_save ',a);s=s[:a]+s[b:]
a=s.index('static size_t make_packet(');b=s.index('static int queue_params(',a)
s=s[:a]+'''static size_t make_packet(void *memory,unsigned int phase) {
 struct camss_params_wb_gain wb={.header={CAMSS_PARAMS_WB_GAIN,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(wb)},.g_gain=1024,.b_gain=1024,.r_gain=1024};
 struct camss_params_lsc lsc={.header={CAMSS_PARAMS_LSC,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(lsc)},.cell_width=66,.cell_height=65,.x_start=2};
 if(phase==0||phase==5||phase==8){lsc.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;lsc.header.size=sizeof(lsc.header);}
 if(phase==7){lsc.cell_width=72;lsc.cell_height=68;lsc.x_start=50;lsc.y_start=18;lsc.subdivision=2;}
 for(unsigned c=0;c<4;c++)for(unsigned y=0;y<13;y++)for(unsigned x=0;x<17;x++){
  unsigned gain=1024;
  if(phase==2)gain=1536;
  if(phase==3)gain=1024+64*x;
  if(phase==4)gain=c==0?1536:c==3?1280:1024;
  if(phase==7)gain=1024+64*y;
  lsc.gains[c][y*17+x]=gain;
 }
 struct params_envelope e={V4L2_ISP_VERSION_V1,sizeof(wb)+lsc.header.size};
 memset(memory,0,params_size);memcpy(memory,&e,sizeof(e));
 memcpy((char*)memory+sizeof(e),&wb,sizeof(wb));
 memcpy((char*)memory+sizeof(e)+sizeof(wb),&lsc,lsc.header.size);
 return sizeof(e)+e.data_size;
}
'''+s[b:]
s=s.replace('static int dequeue_params(unsigned int phase)', 'static unsigned parameter_sequence;\nstatic int dequeue_params(unsigned int phase)')
s=s.replace(' printf("PARAM_DQ phase=', ' parameter_sequence=b.sequence;\n printf("PARAM_DQ phase=')
a=s.index('static int reject_invalid_params(');b=s.index('static int open_params(',a)
s=s[:a]+'''static int reject_invalid_params(void) {
 for(unsigned test=0;test<7;test++){
  size_t size=make_packet(params_map,1);
  struct camss_params_lsc *l=(void*)((char*)params_map+sizeof(struct params_envelope)+sizeof(struct camss_params_wb_gain));
  switch(test){case 0:l->header.flags=3;break;case 1:l->_pad[0]=1;break;case 2:l->gains[0][0]=8192;break;case 3:l->cell_width=17;break;case 4:l->cell_width=64;break;case 5:l->subdivision=4;break;case 6:l->gains[0][0]=1023;break;}
  struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP,.bytesused=size};
  errno=0;if(!call(params_fd,VIDIOC_QBUF,&b)||errno!=EINVAL){errno=EPROTO;return -1;}
  printf("PARAM_REJECT test=%u errno=%d\\n",test,errno);
 }return 0;
}
'''+s[b:]
s=s.replace('sizeof(struct params_envelope)+sizeof(struct camss_params_wb_gain)||', 'sizeof(struct params_envelope)+sizeof(struct camss_params_wb_gain)+sizeof(struct camss_params_lsc)||')
s=s.replace(' phase="stats-open";if(stats_open(&statistics))goto cleanup;\n','')
s=s.replace(' if(stats_close()){perror("stats cleanup");result=1;}\n','')
s=s.replace('  if(stats_streaming&&(frame<102||frame>=108)&&stats_dequeue(frame,argv[2]))goto cleanup;\n','')
a=s.index(' /* Sink restoration propagates');b=s.index(' for(unsigned n=0;n<4;n++)',a);s=s[:a]+s[b:]
a=s.index(' for(unsigned frame=0;');b=s.index('  struct pollfd p={.fd=video',a)
s=s[:a]+''' unsigned wb_phase=0,phase_frames=0;uint64_t previous_hash=0;
 for(unsigned frame=0;wb_phase<9&&frame<288;frame++){
'''+s[b:]
s=s.replace('  if(frame%9==8){char output_path', '  uint64_t frame_hash=hash(data,plane[0].bytesused);\n  bool settled=buffer.sequence>=parameter_sequence+2&&phase_frames>0&&frame_hash==previous_hash;\n  if(settled){char output_path')
s=s.replace('"%s-%u.nv12",argv[2],frame','"%s-phase%u.nv12",argv[2],wb_phase')
s=s.replace('  for(size_t n=0;n<sizes[buffer.index];n++)data[n]=prefill', '  printf("LSC_FRAME phase=%u sequence=%u parameter_sequence=%u settled=%u hash=%016" PRIx64 "\\n",wb_phase,buffer.sequence,parameter_sequence,settled,frame_hash);\n  for(size_t n=0;n<sizes[buffer.index];n++)data[n]=prefill')
s=s.replace('  if(call(video,VIDIOC_QBUF,&buffer))goto cleanup;\n }\n result=0;', '''  if(call(video,VIDIOC_QBUF,&buffer))goto cleanup;
  previous_hash=frame_hash;phase_frames++;
  if(settled){wb_phase++;phase_frames=0;previous_hash=0;if(wb_phase<9&&(queue_params(wb_phase,true)||dequeue_params(wb_phase)))goto cleanup;}
 }
 if(wb_phase!=9){errno=ETIMEDOUT;goto cleanup;}
 result=0;''')
s=s.replace('exposures=150,1200,150','exposure=150')
s=s.replace('off.value=2;if(call(sensor', 'off.value=3;if(call(sensor').replace('sensor_tpg=2', 'sensor_tpg=3')
(HERE/'samurai-lsc.c').write_text(s)
uapi=host.PRIVATE/'host-uapi/linux';uapi.mkdir(parents=True,exist_ok=True)
shutil.copy2(HERE/'kernel/qcom-camss-config.h',uapi/'qcom-camss-config.h')
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I'+str(uapi.parent),'-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera318-lsc-kernel/include/uapi',str(HERE/'samurai-lsc.c'),'-o',str(host.PRIVATE/'samurai-lsc')],capture_output=True)
(host.PRIVATE/'probe-build.log').write_bytes(q.stdout+q.stderr)
print(q.stderr.decode());assert q.returncode==0
print(json.dumps({'compiled':True,'bytes':(host.PRIVATE/'samurai-lsc').stat().st_size}))
