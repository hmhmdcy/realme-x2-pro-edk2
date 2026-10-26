/* Offscreen Vulkan GMEM render/readback with fence-ordered resource churn. */
#include <vulkan/vulkan.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#define CHECK(x) do { VkResult r=(x); if(r!=VK_SUCCESS){fprintf(stderr,"%s returned %d at line %d\n",#x,r,__LINE__);exit(2);} } while(0)
static VkDevice dev; static VkPhysicalDevice phys; static VkQueue queue;
static VkFormat active_format=VK_FORMAT_R8G8B8A8_UNORM;
static VkPhysicalDeviceMemoryProperties memprops;
static uint32_t memory_type(uint32_t bits, VkMemoryPropertyFlags flags) {
 for(uint32_t i=0;i<memprops.memoryTypeCount;i++)
  if((bits&(1u<<i)) && (memprops.memoryTypes[i].propertyFlags&flags)==flags) return i;
 fprintf(stderr,"No memory type for flags %u\n",flags);exit(3);
}
static VkDeviceMemory allocate(VkMemoryRequirements r, VkMemoryPropertyFlags flags) {
 VkMemoryAllocateInfo info={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.allocationSize=r.size,.memoryTypeIndex=memory_type(r.memoryTypeBits,flags)};
 VkDeviceMemory m;CHECK(vkAllocateMemory(dev,&info,NULL,&m));return m;
}
static VkShaderModule shader(const char *name) {
 FILE *f=fopen(name,"rb");if(!f){perror(name);exit(4);} fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);
 uint32_t *code=malloc(n);if(fread(code,1,n,f)!=(size_t)n)exit(4);fclose(f);
 VkShaderModuleCreateInfo info={.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,.codeSize=n,.pCode=code};
 VkShaderModule s;CHECK(vkCreateShaderModule(dev,&info,NULL,&s));free(code);return s;
}
struct image { VkImage image; VkImageView view; VkDeviceMemory mem; };
static struct image image(uint32_t w,uint32_t h,VkSampleCountFlagBits samples,VkImageUsageFlags usage) {
 struct image im;VkImageCreateInfo info={.sType=VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,.imageType=VK_IMAGE_TYPE_2D,.format=active_format,
 .extent={w,h,1},.mipLevels=1,.arrayLayers=1,.samples=samples,.tiling=VK_IMAGE_TILING_OPTIMAL,.usage=usage,.sharingMode=VK_SHARING_MODE_EXCLUSIVE,.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED};
 CHECK(vkCreateImage(dev,&info,NULL,&im.image));VkMemoryRequirements r;vkGetImageMemoryRequirements(dev,im.image,&r);
 im.mem=allocate(r,0);CHECK(vkBindImageMemory(dev,im.image,im.mem,0));
 VkImageViewCreateInfo vi={.sType=VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,.image=im.image,.viewType=VK_IMAGE_VIEW_TYPE_2D,.format=active_format,
 .subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};CHECK(vkCreateImageView(dev,&vi,NULL,&im.view));return im;
}
static void free_image(struct image im) {vkDestroyImageView(dev,im.view,NULL);vkDestroyImage(dev,im.image,NULL);vkFreeMemory(dev,im.mem,NULL);}
struct buffer { VkBuffer buffer; VkDeviceMemory mem; };
static struct buffer buffer(VkDeviceSize size,VkBufferUsageFlags usage,VkMemoryPropertyFlags flags) {
 struct buffer b;VkBufferCreateInfo info={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,.size=size,.usage=usage,.sharingMode=VK_SHARING_MODE_EXCLUSIVE};
 CHECK(vkCreateBuffer(dev,&info,NULL,&b.buffer));VkMemoryRequirements r;vkGetBufferMemoryRequirements(dev,b.buffer,&r);b.mem=allocate(r,flags);
 CHECK(vkBindBufferMemory(dev,b.buffer,b.mem,0));return b;
}
static void free_buffer(struct buffer b){vkDestroyBuffer(dev,b.buffer,NULL);vkFreeMemory(dev,b.mem,NULL);}
int main(int argc,char **argv) {
 setbuf(stdout,NULL);unsigned loops=argc>1?atoi(argv[1]):16;if(!loops||loops>200)return 5;
 VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.pApplicationName="k148-vm-bind-pixel",.apiVersion=VK_API_VERSION_1_2};
 VkInstanceCreateInfo ii={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app};VkInstance instance;CHECK(vkCreateInstance(&ii,NULL,&instance));
 uint32_t n=1;CHECK(vkEnumeratePhysicalDevices(instance,&n,&phys));VkPhysicalDeviceProperties props;vkGetPhysicalDeviceProperties(phys,&props);
 if(props.vendorID!=0x5143||!strstr(props.deviceName,"640")){fprintf(stderr,"Unexpected GPU\n");return 6;}
 printf("GPU=%s api=%u driver=%u\n",props.deviceName,props.apiVersion,props.driverVersion);
 vkGetPhysicalDeviceMemoryProperties(phys,&memprops);uint32_t families=0;vkGetPhysicalDeviceQueueFamilyProperties(phys,&families,NULL);
 VkQueueFamilyProperties *qprops=calloc(families,sizeof(*qprops));vkGetPhysicalDeviceQueueFamilyProperties(phys,&families,qprops);uint32_t family=UINT32_MAX;
 for(uint32_t i=0;i<families;i++){if(qprops[i].queueFlags&VK_QUEUE_GRAPHICS_BIT){family=i;break;}}
 if(family==UINT32_MAX)return 7;
 printf("queue_flags=%u sparse_queue=%d msaa4=%d\n",qprops[family].queueFlags,!!(qprops[family].queueFlags&VK_QUEUE_SPARSE_BINDING_BIT),!!(props.limits.framebufferColorSampleCounts&VK_SAMPLE_COUNT_4_BIT));free(qprops);
 float priority=1;VkDeviceQueueCreateInfo qi={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
 VkDeviceCreateInfo di={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.queueCreateInfoCount=1,.pQueueCreateInfos=&qi};CHECK(vkCreateDevice(phys,&di,NULL,&dev));vkGetDeviceQueue(dev,family,0,&queue);
 VkCommandPoolCreateInfo ci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,.queueFamilyIndex=family};VkCommandPool pool;CHECK(vkCreateCommandPool(dev,&ci,NULL,&pool));
 VkCommandBufferAllocateInfo ai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};VkCommandBuffer cmd;CHECK(vkAllocateCommandBuffers(dev,&ai,&cmd));
 VkShaderModule vert=shader("/var/lib/samurai/k148-tools/probe.vert.spv"),frag=shader("/var/lib/samurai/k148-tools/probe.frag.spv");
 VkPipelineLayoutCreateInfo li={.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};VkPipelineLayout layout;CHECK(vkCreatePipelineLayout(dev,&li,NULL,&layout));
 uint64_t pixels=0;unsigned pause_ms=getenv("K148_PAUSE_MS")?atoi(getenv("K148_PAUSE_MS")):0;
 unsigned variants=getenv("K148_VARIANTS")?atoi(getenv("K148_VARIANTS")):0;
 if(variants>1)return 10;
 unsigned draw_churn=getenv("K148_DRAW_CHURN")?atoi(getenv("K148_DRAW_CHURN")):0;
 if(draw_churn>1)return 11;
 if(pause_ms>5000)return 9;
 for(unsigned iter=0;iter<loops;iter++){
  uint32_t w=iter%3==0?800:iter%3==1?801:1080,h=iter%3==0?600:iter%3==1?603:2259;
  if(variants){static const uint32_t sizes[5][2]={{360,753},{37,21},{1080,2259},{801,603},{320,640}};static const VkFormat formats[3]={VK_FORMAT_R8G8B8A8_UNORM,VK_FORMAT_B8G8R8A8_SRGB,VK_FORMAT_R16G16B16A16_SFLOAT};w=sizes[iter%5][0];h=sizes[iter%5][1];active_format=formats[iter%3];}
  unsigned bytes_per_pixel=active_format==VK_FORMAT_R16G16B16A16_SFLOAT?8:4;
  VkImageFormatProperties fp;CHECK(vkGetPhysicalDeviceImageFormatProperties(phys,active_format,VK_IMAGE_TYPE_2D,VK_IMAGE_TILING_OPTIMAL,VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT,0,&fp));
  int msaa=(iter%2)&&(fp.sampleCounts&VK_SAMPLE_COUNT_4_BIT);VkSampleCountFlagBits samples=msaa?VK_SAMPLE_COUNT_4_BIT:VK_SAMPLE_COUNT_1_BIT;
  struct buffer churn[7];for(unsigned i=0;i<7;i++)churn[i]=buffer(4096*(1+(iter+i)%17),VK_BUFFER_USAGE_TRANSFER_DST_BIT,0);
  struct image color=image(w,h,samples,VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|(msaa?0:VK_IMAGE_USAGE_TRANSFER_SRC_BIT)),resolve={0};if(msaa)resolve=image(w,h,VK_SAMPLE_COUNT_1_BIT,VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT);
  struct buffer readback=buffer((VkDeviceSize)w*h*bytes_per_pixel,VK_BUFFER_USAGE_TRANSFER_DST_BIT,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
  VkAttachmentDescription at[2]={{.format=active_format,.samples=samples,.loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR,.storeOp=msaa?VK_ATTACHMENT_STORE_OP_DONT_CARE:VK_ATTACHMENT_STORE_OP_STORE,
   .stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE,.stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE,.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED,.finalLayout=msaa?VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL:VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL},
   {.format=active_format,.samples=VK_SAMPLE_COUNT_1_BIT,.loadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE,.storeOp=VK_ATTACHMENT_STORE_OP_STORE,.stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE,.stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE,.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED,.finalLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL}};
  VkAttachmentReference ca={0,VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL},ra={1,VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
  VkSubpassDescription sp={.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS,.colorAttachmentCount=1,.pColorAttachments=&ca,.pResolveAttachments=msaa?&ra:NULL};
  VkRenderPassCreateInfo ri={.sType=VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,.attachmentCount=msaa?2:1,.pAttachments=at,.subpassCount=1,.pSubpasses=&sp};VkRenderPass pass;CHECK(vkCreateRenderPass(dev,&ri,NULL,&pass));
  VkImageView views[2]={color.view,resolve.view};VkFramebufferCreateInfo fi={.sType=VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,.renderPass=pass,.attachmentCount=msaa?2:1,.pAttachments=views,.width=w,.height=h,.layers=1};VkFramebuffer fb;CHECK(vkCreateFramebuffer(dev,&fi,NULL,&fb));
  VkPipelineShaderStageCreateInfo stages[2]={{.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,.stage=VK_SHADER_STAGE_VERTEX_BIT,.module=vert,.pName="main"},{.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,.stage=VK_SHADER_STAGE_FRAGMENT_BIT,.module=frag,.pName="main"}};
  VkPipelineVertexInputStateCreateInfo vsi={.sType=VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};VkPipelineInputAssemblyStateCreateInfo ias={.sType=VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST};
  VkViewport vp={0,0,w,h,0,1};VkRect2D sc={{0,0},{w,h}};VkPipelineViewportStateCreateInfo vps={.sType=VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,.viewportCount=1,.pViewports=&vp,.scissorCount=1,.pScissors=&sc};
  VkPipelineRasterizationStateCreateInfo rs={.sType=VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,.polygonMode=VK_POLYGON_MODE_FILL,.cullMode=VK_CULL_MODE_NONE,.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE,.lineWidth=1};
  VkPipelineMultisampleStateCreateInfo mss={.sType=VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,.rasterizationSamples=samples};VkPipelineColorBlendAttachmentState cba={.colorWriteMask=15};VkPipelineColorBlendStateCreateInfo cbs={.sType=VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,.attachmentCount=1,.pAttachments=&cba};
  VkGraphicsPipelineCreateInfo pi={.sType=VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,.stageCount=2,.pStages=stages,.pVertexInputState=&vsi,.pInputAssemblyState=&ias,.pViewportState=&vps,.pRasterizationState=&rs,.pMultisampleState=&mss,.pColorBlendState=&cbs,.layout=layout,.renderPass=pass};VkPipeline pipeline;CHECK(vkCreateGraphicsPipelines(dev,VK_NULL_HANDLE,1,&pi,NULL,&pipeline));
  CHECK(vkResetCommandBuffer(cmd,0));VkCommandBufferBeginInfo bi={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};CHECK(vkBeginCommandBuffer(cmd,&bi));
  for(unsigned i=0;i<7;i++)vkCmdFillBuffer(cmd,churn[i].buffer,0,VK_WHOLE_SIZE,0x12340000+iter+i);
  VkClearValue clear={.color={{0,0,1,1}}};VkRenderPassBeginInfo rbi={.sType=VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,.renderPass=pass,.framebuffer=fb,.renderArea=sc,.clearValueCount=1,.pClearValues=&clear};vkCmdBeginRenderPass(cmd,&rbi,VK_SUBPASS_CONTENTS_INLINE);vkCmdBindPipeline(cmd,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline);unsigned draws=draw_churn&&(iter%2)?128:1;for(unsigned d=0;d<draws;d++)vkCmdDraw(cmd,3,1,0,0);vkCmdEndRenderPass(cmd);
  VkImage target=msaa?resolve.image:color.image;VkImageMemoryBarrier ib={.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT,.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.image=target,.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
  vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,0,NULL,1,&ib);
  VkBufferImageCopy copy={.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},.imageExtent={w,h,1}};vkCmdCopyImageToBuffer(cmd,target,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,readback.buffer,1,&copy);
  VkBufferMemoryBarrier bb={.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_HOST_READ_BIT,.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.buffer=readback.buffer,.size=VK_WHOLE_SIZE};vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,NULL,1,&bb,0,NULL);CHECK(vkEndCommandBuffer(cmd));
  VkFenceCreateInfo fci={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};VkFence fence;CHECK(vkCreateFence(dev,&fci,NULL,&fence));VkSubmitInfo si={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.commandBufferCount=1,.pCommandBuffers=&cmd};CHECK(vkQueueSubmit(queue,1,&si,fence));CHECK(vkWaitForFences(dev,1,&fence,VK_TRUE,10000000000ull));
  uint8_t *data;CHECK(vkMapMemory(dev,readback.mem,0,VK_WHOLE_SIZE,0,(void**)&data));uint64_t mismatches=0;
  for(uint32_t y=0;y<h;y++)for(uint32_t x=0;x<w;x++){size_t o=((size_t)y*w+x)*bytes_per_pixel;unsigned green=(x/32+y/32)&1;if(bytes_per_pixel==8){const uint16_t *v=(const uint16_t *)(data+o);if(v[0]!=0x3c00||v[1]!=(green?0x3c00:0)||v[2]!=0||v[3]!=0x3c00)mismatches++;}else{unsigned red=active_format==VK_FORMAT_B8G8R8A8_SRGB?2:0,blue=2-red;if(data[o+red]!=255||data[o+1]!=(green?255:0)||data[o+blue]!=0||data[o+3]!=255)mismatches++;}}
  vkUnmapMemory(dev,readback.mem);pixels+=(uint64_t)w*h;printf("PIXEL iteration=%u size=%ux%u samples=%u format=%u draws=%u mismatches=%llu\n",iter,w,h,samples,active_format,draws,(unsigned long long)mismatches);
  vkDestroyFence(dev,fence,NULL);vkDestroyPipeline(dev,pipeline,NULL);vkDestroyFramebuffer(dev,fb,NULL);vkDestroyRenderPass(dev,pass,NULL);free_buffer(readback);if(msaa)free_image(resolve);free_image(color);for(unsigned i=0;i<7;i++)free_buffer(churn[i]);
  if(mismatches)return 8;
  if(pause_ms)usleep(pause_ms*1000);
 }
 CHECK(vkDeviceWaitIdle(dev));vkDestroyPipelineLayout(dev,layout,NULL);vkDestroyShaderModule(dev,vert,NULL);vkDestroyShaderModule(dev,frag,NULL);vkDestroyCommandPool(dev,pool,NULL);vkDestroyDevice(dev,NULL);vkDestroyInstance(instance,NULL);
 printf("ALL_PIXELS_PASS iterations=%u pixels=%llu fence_ordered_lifetime=1\n",loops,(unsigned long long)pixels);return 0;
}
