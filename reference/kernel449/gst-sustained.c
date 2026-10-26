/* Exercise libcamerasrc caps negotiation and actual NV12 appsink buffers. */
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/allocators/gstdmabuf.h>
#include <linux/dma-buf.h>
#include <linux/v4l2-subdev.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <signal.h>
static volatile sig_atomic_t interrupted;
static void on_signal(int unused){(void)unused;interrupted=1;}

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
 unsigned target=120;
 const char *setting=getenv("GST_TARGET_FRAMES");
 if(setting){char *end=NULL;unsigned long n=strtoul(setting,&end,10);if(!*setting||*end||n<12||n>10000)return 2;target=(unsigned)n;}
 printf("GST_TARGET frames=%u\n",target);fflush(stdout);
 FILE *status=fopen("/proc/self/status","r");char line[256],capabilities[32]="missing";
 if(status){while(fgets(line,sizeof(line),status))if(sscanf(line,"CapEff: %31s",capabilities)==1)break;fclose(status);}
 printf("APPLICATION_IDENTITY uid=%u euid=%u capeff=%s\n",getuid(),geteuid(),capabilities);fflush(stdout);
 signal(SIGINT,on_signal);signal(SIGTERM,on_signal);
 gst_init(NULL,NULL);
 GstElement *pipeline=gst_pipeline_new(NULL),*source=gst_element_factory_make("libcamerasrc",NULL);
 GstElement *filter=gst_element_factory_make("capsfilter",NULL),*sink=gst_element_factory_make("appsink",NULL);
 if(!pipeline || !source || !filter || !sink)return 3;
 g_object_set(source,"camera-name",argv[1],NULL);
 GstCaps *caps=gst_caps_new_simple("video/x-raw","format",G_TYPE_STRING,"NV12","width",G_TYPE_INT,width,"height",G_TYPE_INT,height,NULL);
 g_object_set(filter,"caps",caps,NULL);gst_caps_unref(caps);
 g_object_set(sink,"sync",FALSE,"max-buffers",2u,"drop",FALSE,"wait-on-eos",FALSE,NULL);
 gst_bin_add_many(GST_BIN(pipeline),source,filter,sink,NULL);
 int result=0;unsigned frames=0;uint64_t previous=0,previous_sequence=0;
 if(!gst_element_link_many(source,filter,sink,NULL) || gst_element_set_state(pipeline,GST_STATE_PLAYING)==GST_STATE_CHANGE_FAILURE)result=4;
 while(!result && !interrupted && frames<target) {
  GstSample *sample=NULL;
  for(unsigned wait=0;wait<50&&!interrupted&&!sample;++wait)sample=gst_app_sink_try_pull_sample(GST_APP_SINK(sink),100*GST_MSECOND);
  if(interrupted){if(sample)gst_sample_unref(sample);result=9;break;}
  if(!sample){result=5;break;}
  GstCaps *actual=gst_sample_get_caps(sample);
  const GstStructure *structure=actual?gst_caps_get_structure(actual,0):NULL;
  int w=0,h=0;const char *format=structure?gst_structure_get_string(structure,"format"):NULL;
  GstBuffer *buffer=gst_sample_get_buffer(sample);uint64_t hash=0;
  if(!structure || !gst_structure_get_int(structure,"width",&w) || !gst_structure_get_int(structure,"height",&h) ||
     w!=width || h!=height || !format || g_strcmp0(format,"NV12") || !buffer ||
     !GST_BUFFER_PTS_IS_VALID(buffer) || (frames && GST_BUFFER_PTS(buffer)<=previous) || GST_BUFFER_OFFSET(buffer)==GST_BUFFER_OFFSET_NONE ||
     (frames && GST_BUFFER_OFFSET(buffer)<=previous_sequence) ||
     GST_BUFFER_FLAG_IS_SET(buffer,GST_BUFFER_FLAG_CORRUPTED) ||
     gst_buffer_get_size(buffer)!=(gsize)width*height*3/2 || sample_buffer(buffer,&hash))result=6;
  if(!result && !frames && getenv("GST_SENSOR_NODE")) {
   int fd=open(getenv("GST_SENSOR_NODE"),O_RDONLY|O_CLOEXEC);
   struct v4l2_subdev_format format={.which=V4L2_SUBDEV_FORMAT_ACTIVE,.pad=0};
   if(fd<0 || ioctl(fd,VIDIOC_SUBDEV_G_FMT,&format))result=6;
   else {printf("GST_SENSOR width=%u height=%u code=%u\n",format.format.width,format.format.height,format.format.code);fflush(stdout);}
   if(fd>=0)close(fd);
  }
  if(!result) {
   previous=GST_BUFFER_PTS(buffer);previous_sequence=GST_BUFFER_OFFSET(buffer);
   printf("GST_IMAGE frame=%u width=%d height=%d bytes=%zu pts=%llu hash=%llu sequence=%llu wall-ns=%llu\n",frames,w,h,gst_buffer_get_size(buffer),(unsigned long long)previous,(unsigned long long)hash,(unsigned long long)previous_sequence,(unsigned long long)g_get_monotonic_time()*1000);fflush(stdout);++frames;
  }
  gst_sample_unref(sample);
 }
 if(interrupted && !result)result=9;
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
