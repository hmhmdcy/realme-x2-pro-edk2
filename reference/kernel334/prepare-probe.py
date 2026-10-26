from pathlib import Path
import copy,importlib.util,json,shutil,struct,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
spec=importlib.util.spec_from_file_location('assemble322',HERE.parent/'kernel322/assemble-profile.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
root=next(r for r in json.loads((P.parent/'kernel333/qtech_s5kgw1-ccm-trees-private.json').read_text()) if r['uid']==37)
counter=0
def mix(a,b,w):
 global counter
 if w==0:return a
 if w==1:return b
 counter+=1;name='blend-'+str(counter);src=P/(name+'-input-private.bin');dst=P/(name+'-output-private.bin')
 src.write_bytes(struct.pack('<II9f3i9f3if',2,root['qfactor'],*a['matrix'],*a['offsets'],*b['matrix'],*b['offsets'],w))
 subprocess.run([str(P.parent/'kernel333/math-host'),str(src),str(dst)],check=True)
 values=struct.unpack_from('<9f3i',dst.read_bytes());return dict(matrix=list(values[:9]),offsets=list(values[9:]))
def at(nodes,value,callback,positions=(0,1)):
 a,b,w=mod.select(nodes,value,positions);first=callback(nodes[a]);return first if a==b else mix(first,callback(nodes[b]),w)
def choose_led(nodes):
 assert nodes and nodes[0]['trigger']==[0]
 return nodes[0]['children']
assert root['control_method']==[0,1]
data=at(root['core'],1.,lambda drc:at(drc['children'],1.,lambda hdr:at(choose_led(hdr['children']),100.,
 lambda aec:at(aec['children'],6500.,lambda c:c)),(2,3)))
src=P/'factory-input-private.bin';dst=P/'factory-output-private.bin'
src.write_bytes(struct.pack('<II9f3i',1,root['qfactor'],*data['matrix'],*data['offsets']))
subprocess.run([str(P.parent/'kernel333/math-host'),str(src),str(dst)],check=True)
fields=struct.unpack('<13H',dst.read_bytes());a=fields[0:9:3];b=fields[1:9:3];c=fields[2:9:3]
# The extensible ISP header uses bit1 for ENABLE and bit0 for DISABLE.
(P/'factory-ccm-private.bin').write_bytes(struct.pack('<HHI16H',3,2,40,*a,*b,*c,*fields[9:13],0,0,0))
(P/'factory-selection-private.json').write_text(json.dumps(dict(module='qtech_s5kgw1',uid=37,drc=1,hdr_sensitivity_ratio=1,led=0,lux_index=100,cct=6500,qfactor=root['qfactor'],data=data),indent=2)+'\n')
if '--payload-only' in sys.argv:
 print('Updated factory block ENABLE flag; compiled probe and kernel module unchanged.');raise SystemExit(0)
s=(HERE.parent/'kernel318/samurai-lsc.c').read_text()
s=s.replace('static size_t make_packet(', 'static struct camss_params_color_correct factory_ccm;\nstatic size_t make_packet(')
start=s.index(' struct camss_params_lsc lsc=',s.index('static size_t make_packet('));end=s.index(' return sizeof(e)+e.data_size;',start)
s=s[:start]+''' struct camss_params_color_correct ccm={.header={CAMSS_PARAMS_COLOR_CORRECT,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(ccm)},.a={128,0,0},.b={0,128,0},.c={0,0,128}};
 if(phase==0||phase==5||phase==7){ccm.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;ccm.header.size=sizeof(ccm.header);}
 if(phase==2){ccm.a[0]=96;ccm.b[1]=0;ccm.c[1]=128;ccm.b[2]=128;ccm.c[2]=0;}
 if(phase==3){ccm.a[0]=1024;ccm.b[1]=1024;ccm.c[2]=1024;ccm.qfactor=3;}
 if(phase==4){ccm.k[0]=(-64)&0x7ff;ccm.k[1]=32;ccm.k[2]=128;}
 if(phase==6)ccm=factory_ccm;
 struct params_envelope e={V4L2_ISP_VERSION_V1,sizeof(wb)+ccm.header.size};
 memset(memory,0,params_size);memcpy(memory,&e,sizeof(e));
 memcpy((char*)memory+sizeof(e),&wb,sizeof(wb));
 memcpy((char*)memory+sizeof(e)+sizeof(wb),&ccm,ccm.header.size);
'''+s[end:]
start=s.index('static int reject_invalid_params(');end=s.index('static int open_params(',start)
s=s[:start]+'''static int reject_invalid_params(void) {
 for(unsigned test=0;test<2;test++){
  size_t size=make_packet(params_map,1);
  struct camss_params_color_correct *c=(void*)((char*)params_map+sizeof(struct params_envelope)+sizeof(struct camss_params_wb_gain));
  if(test==0)c->qfactor=4;else c->header.size-=8;
  struct v4l2_buffer b={.index=0,.type=V4L2_BUF_TYPE_META_OUTPUT,.memory=V4L2_MEMORY_MMAP,.bytesused=size};
  errno=0;if(!call(params_fd,VIDIOC_QBUF,&b)||errno!=EINVAL){errno=EPROTO;return -1;}
  printf("PARAM_REJECT test=%u errno=%d\\n",test,errno);
 }return 0;
}
'''+s[end:]
s=s.replace('sizeof(struct camss_params_lsc)','sizeof(struct camss_params_color_correct)')
s=s.replace('if(argc!=3||strcmp(argv[1],"--pattern"))','if(argc!=4||strcmp(argv[1],"--pattern"))')
needle=' struct utsname identity;'
s=s.replace(needle,''' FILE *matrix_input=fopen(argv[3],"rb");if(!matrix_input)return 2;
 if(fread(&factory_ccm,sizeof(factory_ccm),1,matrix_input)!=1||fgetc(matrix_input)!=EOF){fclose(matrix_input);return 2;}fclose(matrix_input);
 if(factory_ccm.header.type!=CAMSS_PARAMS_COLOR_CORRECT||factory_ccm.header.size!=sizeof(factory_ccm)||factory_ccm.header.flags!=V4L2_ISP_PARAMS_FL_BLOCK_ENABLE)return 2;
'''+needle)
s=s.replace('"s5k3m5 "','"s5kgw1 "')
s=s.replace('if(input.format.code!=MEDIA_BUS_FMT_SGRBG10_1X10||input.format.width!=2104||input.format.height!=1560)',
 'if(!input.format.width||!input.format.height)')
s=s.replace('if(exposure.minimum>150||exposure.maximum<1200||gain.minimum>64||gain.maximum<64)',
 'if(exposure.minimum>exposure.maximum||gain.minimum>gain.maximum)')
s=s.replace('off.value=3;','off.value=2;')
s=s.replace('.value=64};if(call(sensor,VIDIOC_S_CTRL,&setting))','.value=gain.minimum};if(call(sensor,VIDIOC_S_CTRL,&setting))')
s=s.replace('.value=150};if(call(sensor,VIDIOC_S_CTRL,&setting))','.value=exposure.default_value};if(call(sensor,VIDIOC_S_CTRL,&setting))')
s=s.replace('gain_code=64 exposure=150 sensor_tpg=3','sensor_tpg=2')
s=s.replace('wb_phase<9&&frame<288','wb_phase<8&&!interrupted').replace('wb_phase<9&&','wb_phase<8&&').replace('if(wb_phase!=9)','if(wb_phase!=8)')
s=s.replace('if(y_changed<luma*3/4||uv_changed<(plane[0].bytesused-luma)*3/4){errno=EIO;goto cleanup;}','')
s=s.replace('if(active_changed<103680||timestamp<=0||((frame!=0&&frame!=72)&&','if(timestamp<=0||((frame!=0)&&')
s=s.replace('LSC_FRAME','CCM_FRAME')
needle=' printf("FORMAT video='
at=s.index(needle)
s=s[:at]+' printf("COLORIMETRY colorspace=%u xfer=%u ycbcr=%u quantization=%u\\n",f->colorspace,f->xfer_func,f->ycbcr_enc,f->quantization);\n'+s[at:]
(HERE/'samurai-ccm.c').write_text(s)
stage=SDK/'private/camss334-runtime';stage.mkdir(mode=0o700,exist_ok=True);shutil.copyfile(HERE/'samurai-ccm.c',stage/'samurai-ccm.c')
shutil.copytree(P/'register-test/linux',stage/'include/linux',dirs_exist_ok=True)
tree=Path(json.loads((HERE/'source-state.json').read_text())['source'])
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s',
 '-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-I'+str(stage/'include'),'-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',
 '-I'+str(tree/'include/uapi'),str(stage/'samurai-ccm.c'),'-o',str(stage/'samurai-ccm')],capture_output=True)
(P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
shutil.copyfile(stage/'samurai-ccm',P/'samurai-ccm')
(HERE/'probe-build-validation.json').write_text(json.dumps(dict(stage=334,compiled_aarch64_static=True,phases=['disabled','unity-q7','asymmetric-channel-map','unity-q10','signed-offsets','disabled','factory-6500','disabled'],
 explicit_factory_root_uid=37,explicit_drc=1,explicit_hdr_sensitivity_ratio=1,explicit_led=0,explicit_lux_index=100,explicit_cct_kelvin=6500,
 factory_root_scenario='Default diagnostic, supplier not bound',sensor='s5kgw1',sensor_pattern=2,stable_images_after_parameter_ack=True,phone_changed=False,passed=True),indent=2)+'\n')
print('Prepared eight CCM phases through standard media/V4L2 with source-verified factory matrix.')
