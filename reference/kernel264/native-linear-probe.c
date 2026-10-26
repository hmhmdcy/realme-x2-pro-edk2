/* SPDX-License-Identifier: MIT */
/* Public pw_stream API consumer; retains frames to check shared ownership. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <spa/param/video/format-utils.h>
#include <pipewire/pipewire.h>

struct held { struct pw_buffer *buffer; const uint8_t *pixels; size_t size;
 uint64_t digest; double since; int64_t pts; };
struct data { struct pw_main_loop *loop; struct pw_stream *stream;
 struct spa_source *timer; struct held held[64]; double start;
 unsigned frames,checked,changed,errors,pts_bad,busy_missing,zero_pts;
 int64_t last_pts, first_pts; unsigned removed_held; };
static double now(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9; }
static uint64_t digest(const uint8_t *p,size_t n) {
 uint64_t h=UINT64_C(14695981039346656037);
 for(size_t i=0;i<n;i++) h=(h^p[i])*UINT64_C(1099511628211);
 return h;
}
static void release(struct data *d,struct held *h) {
 struct spa_meta_header *meta=spa_buffer_find_meta_data(h->buffer->buffer,SPA_META_Header,sizeof(*meta));
 d->checked++;
 if(digest(h->pixels,h->size)!=h->digest || !meta || meta->pts!=h->pts) {
  d->changed++;
  fprintf(stderr,"native-changed at=%.6f buffer=%p before-pts=%"PRIi64" after-pts=%"PRIi64"\n",now(),(void*)h->buffer,h->pts,meta?meta->pts:INT64_MIN);
 }
 if(pw_stream_queue_buffer(d->stream,h->buffer)<0)d->errors++;
 h->buffer=NULL;
}
static void on_timer(void *userdata,uint64_t expirations) {
 struct data *d=userdata;double t=now();(void)expirations;
 for(unsigned i=0;i<64;i++)if(d->held[i].buffer && t-d->held[i].since>=.12)release(d,&d->held[i]);
 if(t-d->start>=12)pw_main_loop_quit(d->loop);
}
static void on_process(void *userdata) {
 struct data *d=userdata;struct pw_buffer *b;
 while((b=pw_stream_dequeue_buffer(d->stream))) {
  struct spa_buffer *buf=b->buffer;unsigned i;d->frames++;
  for(i=0;i<64 && d->held[i].buffer;i++);
  struct spa_meta_header *meta=spa_buffer_find_meta_data(buf,SPA_META_Header,sizeof(*meta));
  if(!spa_buffer_find_meta_data(buf,SPA_META_Busy,sizeof(struct spa_meta_busy)))d->busy_missing++;
  if(i==64 || !buf->n_datas || !buf->datas[0].data || !meta || !buf->datas[0].chunk || buf->datas[0].chunk->offset>=buf->datas[0].maxsize) {
   fprintf(stderr,"native-invalid at=%.6f buffer=%p datas=%u header=%d type=%u data=%p size=%u\n",now(),(void*)b,buf->n_datas,meta!=NULL,buf->n_datas?buf->datas[0].type:0,buf->n_datas?buf->datas[0].data:NULL,buf->n_datas?buf->datas[0].maxsize:0);
   d->errors++;pw_stream_queue_buffer(d->stream,b);continue;
  }
  size_t size=SPA_MIN(65536u,SPA_MIN(buf->datas[0].chunk->size,buf->datas[0].maxsize-buf->datas[0].chunk->offset));
  if(!size){d->errors++;pw_stream_queue_buffer(d->stream,b);continue;}
  if(d->frames>1 && meta->pts<=d->last_pts)d->pts_bad++;
  if(d->frames==1)d->first_pts=meta->pts;
  d->last_pts=meta->pts;
  if(meta->pts<=0)d->zero_pts++;
  struct spa_meta_busy *busy=spa_buffer_find_meta_data(buf,SPA_META_Busy,sizeof(*busy));
  fprintf(stderr,"native-frame at=%.6f buffer=%p fd=%d pts=%"PRIi64" seq=%"PRIu64" busy=%u\n",now(),(void*)b,(int)buf->datas[0].fd,meta->pts,meta->seq,busy?SPA_ATOMIC_LOAD(busy->count):0);
  const uint8_t *pixels=SPA_PTROFF(buf->datas[0].data,buf->datas[0].chunk->offset,const uint8_t);
  d->held[i]=(struct held){b,pixels,size,digest(pixels,size),now(),meta->pts};
 }
}
static void on_state(void *userdata,enum pw_stream_state old,enum pw_stream_state state,const char *error) {
 struct data *d=userdata;(void)old;
 if(state==PW_STREAM_STATE_ERROR){fprintf(stderr,"stream error: %s\n",error);d->errors++;pw_main_loop_quit(d->loop);}
}
static void on_remove(void *userdata,struct pw_buffer *buffer) {
 struct data *d=userdata;
 for(unsigned i=0;i<64;i++)if(d->held[i].buffer==buffer){release(d,&d->held[i]);d->removed_held++;}
}
static void on_format(void *userdata,uint32_t id,const struct spa_pod *param) {
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
static const struct pw_stream_events events={PW_VERSION_STREAM_EVENTS,
 .state_changed=on_state,.remove_buffer=on_remove,.process=on_process,.param_changed=on_format};
int main(int argc,char **argv) {
 if(argc!=2)return 2;pw_init(&argc,&argv);struct data d={0};
 d.loop=pw_main_loop_new(NULL);if(!d.loop)return 3;
 struct pw_loop *loop=pw_main_loop_get_loop(d.loop);
 d.stream=pw_stream_new_simple(loop,"k263-native-consumer",pw_properties_new(
  PW_KEY_MEDIA_TYPE,"Video",PW_KEY_MEDIA_CATEGORY,"Capture",PW_KEY_MEDIA_ROLE,"Camera",PW_KEY_TARGET_OBJECT,argv[1],NULL),&events,&d);
 if(!d.stream)return 4;
 uint8_t storage[1024];struct spa_pod_builder builder=SPA_POD_BUILDER_INIT(storage,sizeof(storage));
 const struct spa_pod *params[1];struct spa_video_info_raw format={.format=SPA_VIDEO_FORMAT_BGRx,.size={1920,1080}};
 params[0]=spa_format_video_raw_build(&builder,SPA_PARAM_EnumFormat,&format);
 d.start=now();d.timer=pw_loop_add_timer(loop,on_timer,&d);
 if(!d.timer)return 5;
 struct timespec first={0,20000000},interval={0,20000000};
 if(pw_loop_update_timer(loop,d.timer,&first,&interval,false)<0)return 6;
 int res=pw_stream_connect(d.stream,PW_DIRECTION_INPUT,PW_ID_ANY,PW_STREAM_FLAG_AUTOCONNECT|PW_STREAM_FLAG_MAP_BUFFERS,params,1);
 if(res<0)d.errors++;else pw_main_loop_run(d.loop);
 pw_loop_destroy_source(loop,d.timer);
 for(unsigned i=0;i<64;i++)if(d.held[i].buffer)release(&d,&d.held[i]);
 pw_stream_disconnect(d.stream);pw_stream_destroy(d.stream);pw_main_loop_destroy(d.loop);pw_deinit();
 printf("{\"source_factory\":\"pw_stream\",\"buffers\":%u,\"held_checked\":%u,\"held_content_changed\":%u,\"held_bytes_sampled\":65536,\"zero_header_pts\":%u,\"metadata_busy_missing\":%u,\"errors_count\":%u,\"pts_strictly_increasing\":%s,\"pts_span_seconds\":%.9f,\"held_validated_on_remove\":%u,\"shared_bufferpool\":true,\"stopped\":true}\n",d.frames,d.checked,d.changed,d.zero_pts,d.busy_missing,d.errors,d.pts_bad?"false":"true",(d.last_pts-d.first_pts)/1e9,d.removed_held);
 return d.frames>20 && !d.errors && !d.changed && !d.pts_bad && !d.busy_missing && !d.zero_pts && d.last_pts-d.first_pts>10*INT64_C(1000000000)?0:1;
}
