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
 unsigned frames,checked,changed,errors,pts_bad,busy_missing;
 int64_t last_pts; };
static double now(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9; }
static uint64_t digest(const uint8_t *p,size_t n) {
 uint64_t h=UINT64_C(14695981039346656037);
 for(size_t i=0;i<n;i++) h=(h^p[i])*UINT64_C(1099511628211);
 return h;
}
static void release(struct data *d,struct held *h) {
 struct spa_meta_header *meta=spa_buffer_find_meta_data(h->buffer->buffer,SPA_META_Header,sizeof(*meta));
 d->checked++;
 if(digest(h->pixels,h->size)!=h->digest || !meta || meta->pts!=h->pts) d->changed++;
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
   d->errors++;pw_stream_queue_buffer(d->stream,b);continue;
  }
  size_t size=SPA_MIN(65536u,SPA_MIN(buf->datas[0].chunk->size,buf->datas[0].maxsize-buf->datas[0].chunk->offset));
  if(!size){d->errors++;pw_stream_queue_buffer(d->stream,b);continue;}
  if(d->frames>1 && meta->pts<=d->last_pts)d->pts_bad++;
  d->last_pts=meta->pts;
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
 for(unsigned i=0;i<64;i++)if(d->held[i].buffer==buffer){d->held[i].buffer=NULL;d->errors++;}
}
static const struct pw_stream_events events={PW_VERSION_STREAM_EVENTS,
 .state_changed=on_state,.remove_buffer=on_remove,.process=on_process};
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
 printf("{\"source_factory\":\"pw_stream\",\"buffers\":%u,\"held_checked\":%u,\"held_content_changed\":%u,\"held_bytes_sampled\":65536,\"metadata_busy_missing\":%u,\"errors_count\":%u,\"pts_strictly_increasing\":%s,\"shared_bufferpool\":true,\"stopped\":true}\n",d.frames,d.checked,d.changed,d.busy_missing,d.errors,d.pts_bad?"false":"true");
 return d.frames>20 && !d.errors && !d.changed && !d.pts_bad && !d.busy_missing?0:1;
}
