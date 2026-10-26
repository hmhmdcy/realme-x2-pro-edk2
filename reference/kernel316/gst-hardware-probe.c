/* Exercise libcamerasrc caps negotiation and actual NV12 appsink buffers. */
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/allocators/gstdmabuf.h>
#include <linux/dma-buf.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

static int sample_buffer(GstBuffer *buffer,uint64_t *hash) {
 int fds[16],count=0,result=0;
 for(guint i=0;i<gst_buffer_n_memory(buffer);++i) {
  GstMemory *memory=gst_buffer_peek_memory(buffer,i);
  if(!gst_is_dmabuf_memory(memory))continue;
  int fd=gst_dmabuf_memory_get_fd(memory),found=0;
  for(int j=0;j<count;++j)found|=fds[j]==fd;
  if(found)continue;
  if(count==16){result=1;break;}
  struct dma_buf_sync sync={.flags=DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ};
  if(ioctl(fd,DMA_BUF_IOCTL_SYNC,&sync)){result=1;break;}
  fds[count++]=fd;
 }
 GstMapInfo map=GST_MAP_INFO_INIT;
 if(!result && gst_buffer_map(buffer,&map,GST_MAP_READ)) {
  uint64_t value=1469598103934665603ULL;unsigned nonzero=0;
  size_t step=map.size/4096;if(!step)step=1;
  for(size_t i=0;i<map.size;i+=step){value=(value^map.data[i])*1099511628211ULL;nonzero+=map.data[i]!=0;}
  *hash=value;if(!nonzero)result=1;
  gst_buffer_unmap(buffer,&map);
 } else result=1;
 for(int i=0;i<count;++i) {
  struct dma_buf_sync sync={.flags=DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ};
  if(ioctl(fds[i],DMA_BUF_IOCTL_SYNC,&sync))result=1;
 }
 return result;
}
int main(int argc,char **argv) {
 if(argc!=4)return 2;
 printf("APPLICATION_PROCESS pid=%d\n",getpid());fflush(stdout);
 const int width=atoi(argv[2]),height=atoi(argv[3]);
 gst_init(NULL,NULL);
 GstElement *pipeline=gst_pipeline_new(NULL),*source=gst_element_factory_make("libcamerasrc",NULL);
 GstElement *filter=gst_element_factory_make("capsfilter",NULL),*sink=gst_element_factory_make("appsink",NULL);
 if(!pipeline || !source || !filter || !sink)return 3;
 g_object_set(source,"camera-name",argv[1],NULL);
 GstCaps *caps=gst_caps_new_simple("video/x-raw","format",G_TYPE_STRING,"NV12","width",G_TYPE_INT,width,"height",G_TYPE_INT,height,NULL);
 g_object_set(filter,"caps",caps,NULL);gst_caps_unref(caps);
 g_object_set(sink,"sync",FALSE,"max-buffers",2u,"drop",FALSE,"wait-on-eos",FALSE,NULL);
 gst_bin_add_many(GST_BIN(pipeline),source,filter,sink,NULL);
 int result=0;unsigned frames=0;uint64_t previous=0;
 if(!gst_element_link_many(source,filter,sink,NULL) || gst_element_set_state(pipeline,GST_STATE_PLAYING)==GST_STATE_CHANGE_FAILURE)result=4;
 while(!result && frames<12) {
  GstSample *sample=gst_app_sink_try_pull_sample(GST_APP_SINK(sink),5*GST_SECOND);
  if(!sample){result=5;break;}
  GstCaps *actual=gst_sample_get_caps(sample);
  const GstStructure *structure=actual?gst_caps_get_structure(actual,0):NULL;
  int w=0,h=0;const char *format=structure?gst_structure_get_string(structure,"format"):NULL;
  GstBuffer *buffer=gst_sample_get_buffer(sample);uint64_t hash=0;
  if(!structure || !gst_structure_get_int(structure,"width",&w) || !gst_structure_get_int(structure,"height",&h) ||
     w!=width || h!=height || !format || g_strcmp0(format,"NV12") || !buffer ||
     !GST_BUFFER_PTS_IS_VALID(buffer) || (frames && GST_BUFFER_PTS(buffer)<=previous) || sample_buffer(buffer,&hash))result=6;
  if(!result) {
   previous=GST_BUFFER_PTS(buffer);
   printf("GST_IMAGE frame=%u width=%d height=%d bytes=%zu pts=%llu hash=%llu\n",frames,w,h,gst_buffer_get_size(buffer),(unsigned long long)previous,(unsigned long long)hash);fflush(stdout);++frames;
  }
  gst_sample_unref(sample);
 }
 GstBus *bus=gst_element_get_bus(pipeline);GstMessage *message;unsigned errors=0;
 while((message=gst_bus_pop_filtered(bus,GST_MESSAGE_ERROR))) {
  GError *error=NULL;gchar *debug=NULL;gst_message_parse_error(message,&error,&debug);
  fprintf(stderr,"GStreamer error: %s (%s)\n",error?error->message:"unknown",debug?debug:"");
  g_clear_error(&error);g_free(debug);gst_message_unref(message);++errors;
 }
 gst_object_unref(bus);
 if(gst_element_set_state(pipeline,GST_STATE_NULL)==GST_STATE_CHANGE_FAILURE && !result)result=7;
 gst_element_get_state(pipeline,NULL,NULL,2*GST_SECOND);gst_object_unref(pipeline);
 if(errors && !result)result=8;
 printf("GST_RESULT frames=%u width=%d height=%d bus-errors=%u result=%d\n",frames,width,height,errors,result);
 return result;
}
