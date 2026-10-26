"""Explicitly negotiate CPU-mappable data and timestamps across pool changes."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel264');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire264-native-linear';assert not W.exists();W.mkdir()
s=(R/'native-diagnostic-probe.c').read_text()
needle='static const struct pw_stream_events events=';i=s.index(needle)
handler='''static void on_format(void *userdata,uint32_t id,const struct spa_pod *param) {
 struct data *d=userdata;
 if(id!=SPA_PARAM_Format || !param)return;
 struct spa_video_info_raw format={0};
 if(spa_format_video_raw_parse(param,&format)<0 || format.format!=SPA_VIDEO_FORMAT_BGRx || format.size.width!=1920 || format.size.height!=1080) {
  d->errors++;pw_main_loop_quit(d->loop);return;
 }
 uint8_t storage[1024];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(storage,sizeof(storage));
 const struct spa_pod *params[2];
 params[0]=spa_pod_builder_add_object(&builder,SPA_TYPE_OBJECT_ParamBuffers,SPA_PARAM_Buffers,
  SPA_PARAM_BUFFERS_buffers,SPA_POD_CHOICE_RANGE_Int(8,2,64),
  SPA_PARAM_BUFFERS_blocks,SPA_POD_Int(1),
  SPA_PARAM_BUFFERS_size,SPA_POD_Int(1920*1080*4),
  SPA_PARAM_BUFFERS_stride,SPA_POD_Int(1920*4),
  SPA_PARAM_BUFFERS_dataType,SPA_POD_CHOICE_FLAGS_Int(1<<SPA_DATA_MemFd));
 params[1]=spa_pod_builder_add_object(&builder,SPA_TYPE_OBJECT_ParamMeta,SPA_PARAM_Meta,
  SPA_PARAM_META_type,SPA_POD_Id(SPA_META_Header),
  SPA_PARAM_META_size,SPA_POD_Int(sizeof(struct spa_meta_header)));
 if(pw_stream_update_params(d->stream,params,2)<0){d->errors++;pw_main_loop_quit(d->loop);}
}
'''
s=s[:i]+handler+s[i:]
s=s.replace('.state_changed=on_state,.remove_buffer=on_remove,.process=on_process}', '.state_changed=on_state,.remove_buffer=on_remove,.process=on_process,.param_changed=on_format}')
needle='''   d->errors++;pw_stream_queue_buffer(d->stream,b);continue;'''
assert s.count(needle)==1
s=s.replace(needle,'''   fprintf(stderr,"native-invalid at=%.6f buffer=%p datas=%u header=%d type=%u data=%p size=%u\\n",now(),(void*)b,buf->n_datas,meta!=NULL,buf->n_datas?buf->datas[0].type:0,buf->n_datas?buf->datas[0].data:NULL,buf->n_datas?buf->datas[0].maxsize:0);
   d->errors++;pw_stream_queue_buffer(d->stream,b);continue;''')
(R/'native-linear-probe.c').write_text(s);(W/'probe.c').write_text(s)
q=subprocess.run(['chroot',str(SDK),'gcc','-std=gnu11','-O2','-Wall','-Wextra','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2','/work/pipewire264-native-linear/probe.c','/work/pipewire263-broadcast/build/src/pipewire/libpipewire-0.3.so.0.1609.0','-o','/work/pipewire264-native-linear/probe'],capture_output=True)
(P/'native-linear-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2500:]
shutil.copyfile(W/'probe',P/'native-linear-probe')
d=dict(compiled=True,sha256=hashlib.sha256((W/'probe').read_bytes()).hexdigest(),public_pw_stream_api=True,explicit_memory_type='MemFd',explicit_header_meta=True,does_not_filter_zero_pts=True)
(R/'native-linear-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
