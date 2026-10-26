/* Public PipeWire video consumer for the hardware NV12 node. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <linux/dma-buf.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <spa/param/video/format-utils.h>
#include <pipewire/pipewire.h>
struct capture {
 struct pw_main_loop *loop;struct pw_stream *stream;struct spa_source *timer;
 unsigned frames,errors;int format;int64_t pts;double start;
};
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static void tick(void *userdata,uint64_t expirations){struct capture *c=userdata;(void)expirations;if(now()-c->start>15){c->errors++;pw_main_loop_quit(c->loop);}}
static void state(void *userdata,enum pw_stream_state old,enum pw_stream_state current,const char *error){
 struct capture *c=userdata;(void)old;if(current==PW_STREAM_STATE_ERROR){fprintf(stderr,"PW error: %s\n",error);c->errors++;pw_main_loop_quit(c->loop);}
}
static void param(void *userdata,uint32_t id,const struct spa_pod *pod){
 struct capture *c=userdata;if(id!=SPA_PARAM_Format || !pod)return;
 struct spa_video_info_raw info={0};
 if(spa_format_video_raw_parse(pod,&info)<0 || info.format!=SPA_VIDEO_FORMAT_NV12 || info.size.width!=640 || info.size.height!=480){c->errors++;pw_main_loop_quit(c->loop);return;}
 c->format=1;
 uint8_t storage[256];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(storage,sizeof(storage));
 const struct spa_pod *params[]={spa_pod_builder_add_object(&builder,
  SPA_TYPE_OBJECT_ParamMeta,SPA_PARAM_Meta,
  SPA_PARAM_META_type,SPA_POD_Id(SPA_META_Header),
  SPA_PARAM_META_size,SPA_POD_Int(sizeof(struct spa_meta_header)))};
 if(pw_stream_update_params(c->stream,params,1)<0){c->errors++;pw_main_loop_quit(c->loop);}
}
static void process(void *userdata){
 struct capture *c=userdata;struct pw_buffer *buffer;
 while((buffer=pw_stream_dequeue_buffer(c->stream))) {
  struct spa_buffer *b=buffer->buffer;
  struct spa_meta_header *meta=spa_buffer_find_meta_data(b,SPA_META_Header,sizeof(*meta));
  struct spa_data *data=b->n_datas?b->datas:NULL;uint64_t hash=1469598103934665603ULL;
  int bad=!data || !data->chunk || !data->chunk->size || data->chunk->offset>=data->maxsize || !meta || (c->frames && meta->pts<=c->pts);
  void *mapping=MAP_FAILED;size_t mapped_size=0;const uint8_t *pixels=data?data->data:NULL;
  /* MAP_BUFFERS maps MemFd, but clients must map DMA-BUF themselves. */
  if(!bad && !pixels && data->type==SPA_DATA_DmaBuf && data->fd>=0){
   mapped_size=(size_t)data->mapoffset+data->maxsize;
   mapping=mmap(NULL,mapped_size,PROT_READ,MAP_SHARED,(int)data->fd,0);
   if(mapping!=MAP_FAILED)pixels=SPA_PTROFF(mapping,data->mapoffset,const uint8_t);
  }
  bad|=!pixels;
  int sync_read=0;
  if(!bad && data->type==SPA_DATA_DmaBuf){struct dma_buf_sync sync={.flags=DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ};bad=ioctl(data->fd,DMA_BUF_IOCTL_SYNC,&sync)!=0;sync_read=!bad;}
  if(!bad){
   size_t bytes=SPA_MIN(data->chunk->size,data->maxsize-data->chunk->offset),step=SPA_MAX(1u,bytes/4096);unsigned nonzero=0;
   const uint8_t *image=SPA_PTROFF(pixels,data->chunk->offset,const uint8_t);
   for(size_t i=0;i<bytes;i+=step){hash=(hash^image[i])*1099511628211ULL;nonzero+=image[i]!=0;}
   bad=!nonzero;c->pts=meta->pts;
   printf("PW_IMAGE frame=%u bytes=%zu pts=%lld hash=%llu type=%u client-mapped=%d\n",c->frames,bytes,(long long)c->pts,(unsigned long long)hash,data->type,mapping!=MAP_FAILED);fflush(stdout);
  }
  if(sync_read){struct dma_buf_sync sync={.flags=DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ};bad|=ioctl(data->fd,DMA_BUF_IOCTL_SYNC,&sync)!=0;}
  if(mapping!=MAP_FAILED)munmap(mapping,mapped_size);
  if(bad)fprintf(stderr,"PW buffer rejected: planes=%u type=%u data=%p maxsize=%u mapoffset=%u chunk=%u offset=%u header=%d pts=%lld\n",
   b->n_datas,data?data->type:0,data?data->data:NULL,data?data->maxsize:0,data?data->mapoffset:0,
   data && data->chunk?data->chunk->size:0,data && data->chunk?data->chunk->offset:0,meta!=NULL,meta?(long long)meta->pts:0LL);
  if(pw_stream_queue_buffer(c->stream,buffer)<0)bad=1;
  if(bad)c->errors++;else c->frames++;
  if(c->errors || c->frames>=12){pw_main_loop_quit(c->loop);break;}
 }
}
static const struct pw_stream_events events={PW_VERSION_STREAM_EVENTS,.state_changed=state,.param_changed=param,.process=process};
struct discovery {struct pw_main_loop *loop;int sequence;unsigned count,errors;};
static void global(void *userdata,uint32_t id,uint32_t permissions,const char *type,uint32_t version,const struct spa_dict *props){
 struct discovery *d=userdata;(void)permissions;(void)version;
 if(strcmp(type,PW_TYPE_INTERFACE_Node) || !props)return;
 const char *media=spa_dict_lookup(props,PW_KEY_MEDIA_CLASS);
 if(!media || strcmp(media,"Video/Source"))return;
 const char *name=spa_dict_lookup(props,PW_KEY_NODE_NAME),*serial=spa_dict_lookup(props,PW_KEY_OBJECT_SERIAL),*path=spa_dict_lookup(props,"api.libcamera.path");
 printf("PW_NODE id=%u name=%s serial=%s path=%s\n",id,name?name:"-",serial?serial:"-",path?path:"-");d->count++;
}
static void core_done(void *userdata,uint32_t id,int sequence){struct discovery *d=userdata;if(id==PW_ID_CORE && sequence==d->sequence)pw_main_loop_quit(d->loop);}
static void core_error(void *userdata,uint32_t id,int sequence,int result,const char *message){struct discovery *d=userdata;(void)id;(void)sequence;(void)result;fprintf(stderr,"PW core error: %s\n",message);d->errors++;pw_main_loop_quit(d->loop);}
static int list_nodes(void){
 struct discovery d={0};d.loop=pw_main_loop_new(NULL);if(!d.loop)return 3;
 struct pw_context *context=pw_context_new(pw_main_loop_get_loop(d.loop),NULL,0);if(!context)return 3;
 struct pw_core *core=pw_context_connect(context,NULL,0);if(!core)return 3;
 struct pw_registry *registry=pw_core_get_registry(core,PW_VERSION_REGISTRY,0);struct spa_hook registry_listener,core_listener;
 static const struct pw_registry_events registry_events={PW_VERSION_REGISTRY_EVENTS,.global=global};
 static const struct pw_core_events core_events={PW_VERSION_CORE_EVENTS,.done=core_done,.error=core_error};
 pw_registry_add_listener(registry,&registry_listener,&registry_events,&d);pw_core_add_listener(core,&core_listener,&core_events,&d);
 d.sequence=pw_core_sync(core,PW_ID_CORE,0);pw_main_loop_run(d.loop);
 spa_hook_remove(&registry_listener);spa_hook_remove(&core_listener);pw_proxy_destroy((struct pw_proxy *)registry);
 pw_core_disconnect(core);pw_context_destroy(context);pw_main_loop_destroy(d.loop);
 printf("PW_NODES count=%u errors=%u\n",d.count,d.errors);return d.errors?1:0;
}
int main(int argc,char **argv){
 if(argc!=2)return 2;printf("APPLICATION_PROCESS pid=%d\n",getpid());fflush(stdout);
 pw_init(&argc,&argv);if(!strcmp(argv[1],"--list")){int result=list_nodes();pw_deinit();return result;}
 struct capture c={0};c.loop=pw_main_loop_new(NULL);if(!c.loop)return 3;
 struct pw_loop *loop=pw_main_loop_get_loop(c.loop);
 c.stream=pw_stream_new_simple(loop,"camss316-hardware-consumer",pw_properties_new(PW_KEY_MEDIA_TYPE,"Video",PW_KEY_MEDIA_CATEGORY,"Capture",PW_KEY_MEDIA_ROLE,"Camera",PW_KEY_TARGET_OBJECT,argv[1],NULL),&events,&c);
 if(!c.stream)return 4;
 uint8_t storage[1024];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(storage,sizeof(storage));
 struct spa_video_info_raw info={.format=SPA_VIDEO_FORMAT_NV12,.size={640,480},.framerate={30,1}};
 const struct spa_pod *params[]={spa_format_video_raw_build(&builder,SPA_PARAM_EnumFormat,&info)};
 c.start=now();c.timer=pw_loop_add_timer(loop,tick,&c);if(!c.timer)return 5;
 struct timespec first={1,0},interval={1,0};pw_loop_update_timer(loop,c.timer,&first,&interval,false);
 if(pw_stream_connect(c.stream,PW_DIRECTION_INPUT,PW_ID_ANY,PW_STREAM_FLAG_AUTOCONNECT|PW_STREAM_FLAG_MAP_BUFFERS,params,1)<0)c.errors++;
 else pw_main_loop_run(c.loop);
 pw_loop_destroy_source(loop,c.timer);pw_stream_disconnect(c.stream);pw_stream_destroy(c.stream);pw_main_loop_destroy(c.loop);pw_deinit();
 int result=c.frames>=12 && c.format && !c.errors?0:1;
 printf("PW_RESULT frames=%u format-accepted=%d errors=%u result=%d\n",c.frames,c.format,c.errors,result);return result;
}
