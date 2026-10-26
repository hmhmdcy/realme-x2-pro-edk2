/* Vulkan sparse remap and buffer-address capture/replay on the real device. */
#include <vulkan/vulkan.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <string.h>
#define CHECK(x) do{VkResult r=(x);if(r){fprintf(stderr,"%s returned %d line %d\n",#x,r,__LINE__);exit(2);}}while(0)
static VkDevice dev;static VkPhysicalDeviceMemoryProperties mp;
static unsigned type(uint32_t bits,VkMemoryPropertyFlags flags){for(unsigned i=0;i<mp.memoryTypeCount;i++)if((bits&(1u<<i))&&(mp.memoryTypes[i].propertyFlags&flags)==flags)return i;exit(3);}
static VkDeviceMemory alloc(VkDeviceSize size,unsigned mt,void *next){VkMemoryAllocateInfo a={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.pNext=next,.allocationSize=size,.memoryTypeIndex=mt};VkDeviceMemory m;CHECK(vkAllocateMemory(dev,&a,NULL,&m));return m;}
static VkBuffer buf(VkDeviceSize size,VkBufferCreateFlags flags,VkBufferUsageFlags usage,void *next){VkBufferCreateInfo a={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,.pNext=next,.flags=flags,.size=size,.usage=usage};VkBuffer b;CHECK(vkCreateBuffer(dev,&a,NULL,&b));return b;}
static void wait(VkFence f){CHECK(vkWaitForFences(dev,1,&f,VK_TRUE,10000000000ull));CHECK(vkResetFences(dev,1,&f));}
int main(int argc,char **argv){
 setbuf(stdout,NULL);unsigned loops=argc>1?atoi(argv[1]):16;if(!loops||loops>200)return 1;
 VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.apiVersion=VK_API_VERSION_1_2};VkInstanceCreateInfo ic={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app};VkInstance in;CHECK(vkCreateInstance(&ic,NULL,&in));
 VkPhysicalDevice ph;uint32_t n=1;CHECK(vkEnumeratePhysicalDevices(in,&n,&ph));VkPhysicalDeviceProperties props;vkGetPhysicalDeviceProperties(ph,&props);if(props.vendorID!=0x5143||!strstr(props.deviceName,"640"))return 4;
 VkPhysicalDeviceVulkan12Features f12={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES};VkPhysicalDeviceFeatures2 f2={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,.pNext=&f12};vkGetPhysicalDeviceFeatures2(ph,&f2);
 printf("FEATURES sparseBinding=%u sparseResidencyBuffer=%u bufferDeviceAddress=%u captureReplay=%u\n",f2.features.sparseBinding,f2.features.sparseResidencyBuffer,f12.bufferDeviceAddress,f12.bufferDeviceAddressCaptureReplay);
 if(!f2.features.sparseBinding||!f12.bufferDeviceAddress||!f12.bufferDeviceAddressCaptureReplay)return 5;
 uint32_t nf=0;vkGetPhysicalDeviceQueueFamilyProperties(ph,&nf,NULL);VkQueueFamilyProperties *qp=calloc(nf,sizeof(*qp));vkGetPhysicalDeviceQueueFamilyProperties(ph,&nf,qp);unsigned family=UINT32_MAX;
 for(unsigned i=0;i<nf;i++)if((qp[i].queueFlags&(VK_QUEUE_GRAPHICS_BIT|VK_QUEUE_SPARSE_BINDING_BIT))==(VK_QUEUE_GRAPHICS_BIT|VK_QUEUE_SPARSE_BINDING_BIT)){family=i;break;}free(qp);if(family==UINT32_MAX)return 6;
 VkPhysicalDeviceFeatures feats={.sparseBinding=VK_TRUE};VkPhysicalDeviceVulkan12Features enable12={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES,.bufferDeviceAddress=VK_TRUE,.bufferDeviceAddressCaptureReplay=VK_TRUE};
 float priority=1;VkDeviceQueueCreateInfo qi={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};VkDeviceCreateInfo dc={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.pNext=&enable12,.queueCreateInfoCount=1,.pQueueCreateInfos=&qi,.pEnabledFeatures=&feats};CHECK(vkCreateDevice(ph,&dc,NULL,&dev));VkQueue q;vkGetDeviceQueue(dev,family,0,&q);vkGetPhysicalDeviceMemoryProperties(ph,&mp);
 VkCommandPoolCreateInfo pc={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,.queueFamilyIndex=family};VkCommandPool pool;CHECK(vkCreateCommandPool(dev,&pc,NULL,&pool));VkCommandBufferAllocateInfo ac={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};VkCommandBuffer cmd;CHECK(vkAllocateCommandBuffers(dev,&ac,&cmd));
 VkFenceCreateInfo fc={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};VkFence fence;CHECK(vkCreateFence(dev,&fc,NULL,&fence));VkSemaphoreCreateInfo sc={.sType=VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};VkSemaphore bound;CHECK(vkCreateSemaphore(dev,&sc,NULL,&bound));
 VkDeviceSize bytes=256*1024;VkBuffer sparse=buf(bytes,VK_BUFFER_CREATE_SPARSE_BINDING_BIT,VK_BUFFER_USAGE_TRANSFER_SRC_BIT|VK_BUFFER_USAGE_TRANSFER_DST_BIT,NULL);VkMemoryRequirements sr;vkGetBufferMemoryRequirements(dev,sparse,&sr);VkDeviceMemory banks[2]={alloc(sr.size,type(sr.memoryTypeBits,0),NULL),alloc(sr.size,type(sr.memoryTypeBits,0),NULL)};
 VkBuffer read=buf(bytes,0,VK_BUFFER_USAGE_TRANSFER_DST_BIT,NULL);VkMemoryRequirements rr;vkGetBufferMemoryRequirements(dev,read,&rr);VkDeviceMemory rm=alloc(rr.size,type(rr.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT),NULL);CHECK(vkBindBufferMemory(dev,read,rm,0));uint32_t *mapped;CHECK(vkMapMemory(dev,rm,0,VK_WHOLE_SIZE,0,(void**)&mapped));
 for(unsigned iter=0;iter<loops;iter++){
  VkSparseMemoryBind bind={.resourceOffset=0,.size=sr.size,.memory=banks[iter%2]};VkSparseBufferMemoryBindInfo binfo={.buffer=sparse,.bindCount=1,.pBinds=&bind};VkBindSparseInfo bi={.sType=VK_STRUCTURE_TYPE_BIND_SPARSE_INFO,.bufferBindCount=1,.pBufferBinds=&binfo,.signalSemaphoreCount=1,.pSignalSemaphores=&bound};CHECK(vkQueueBindSparse(q,1,&bi,VK_NULL_HANDLE));
  CHECK(vkResetCommandBuffer(cmd,0));VkCommandBufferBeginInfo cb={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};CHECK(vkBeginCommandBuffer(cmd,&cb));uint32_t pattern=0x12340000u+iter;vkCmdFillBuffer(cmd,sparse,0,bytes,pattern);
  VkBufferMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT,.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.buffer=sparse,.size=VK_WHOLE_SIZE};vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,1,&barrier,0,NULL);
  VkBufferCopy copy={0,0,bytes};vkCmdCopyBuffer(cmd,sparse,read,1,&copy);barrier.buffer=read;barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,NULL,1,&barrier,0,NULL);CHECK(vkEndCommandBuffer(cmd));
  VkPipelineStageFlags stage=VK_PIPELINE_STAGE_TRANSFER_BIT;VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.waitSemaphoreCount=1,.pWaitSemaphores=&bound,.pWaitDstStageMask=&stage,.commandBufferCount=1,.pCommandBuffers=&cmd};CHECK(vkQueueSubmit(q,1,&submit,fence));wait(fence);
  unsigned bad=0;for(unsigned i=0;i<bytes/4;i++)if(mapped[i]!=pattern)bad++;printf("SPARSE_REMAP iteration=%u bank=%u mismatches=%u\n",iter,iter%2,bad);if(bad)return 7;
 }
 VkSparseMemoryBind unmap={.resourceOffset=0,.size=sr.size,.memory=VK_NULL_HANDLE};VkSparseBufferMemoryBindInfo uinfo={.buffer=sparse,.bindCount=1,.pBinds=&unmap};VkBindSparseInfo ui={.sType=VK_STRUCTURE_TYPE_BIND_SPARSE_INFO,.bufferBindCount=1,.pBufferBinds=&uinfo};CHECK(vkQueueBindSparse(q,1,&ui,fence));wait(fence);
 vkUnmapMemory(dev,rm);vkDestroyBuffer(dev,read,NULL);vkFreeMemory(dev,rm,NULL);vkDestroyBuffer(dev,sparse,NULL);for(unsigned i=0;i<2;i++)vkFreeMemory(dev,banks[i],NULL);
 uint64_t opaque_buffer=0,opaque_memory=0,device_address=0;
 const char *capture_input=getenv("K148_CAPTURE_INPUT"),*capture_output=getenv("K148_CAPTURE_OUTPUT");
 /* Turnip uses the memory address for non-sparse buffers; their opaque
  * buffer capture address is legitimately zero. */
 if(capture_input){FILE *f=fopen(capture_input,"r");if(!f||fscanf(f,"%" SCNu64 " %" SCNu64 " %" SCNu64,&opaque_buffer,&opaque_memory,&device_address)!=3)return 9;fclose(f);if(!opaque_memory||!device_address)return 9;}
 VkBuffer cr=buf(69632,0,VK_BUFFER_USAGE_TRANSFER_DST_BIT,NULL);VkMemoryRequirements crr;vkGetBufferMemoryRequirements(dev,cr,&crr);VkDeviceMemory crm=alloc(crr.size,type(crr.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT),NULL);CHECK(vkBindBufferMemory(dev,cr,crm,0));CHECK(vkMapMemory(dev,crm,0,VK_WHOLE_SIZE,0,(void**)&mapped));
 for(unsigned replay=0;replay<2;replay++){
  VkBufferOpaqueCaptureAddressCreateInfo bc={.sType=VK_STRUCTURE_TYPE_BUFFER_OPAQUE_CAPTURE_ADDRESS_CREATE_INFO,.opaqueCaptureAddress=opaque_buffer};VkBuffer b=buf(69632,VK_BUFFER_CREATE_DEVICE_ADDRESS_CAPTURE_REPLAY_BIT,VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT|VK_BUFFER_USAGE_TRANSFER_DST_BIT|VK_BUFFER_USAGE_TRANSFER_SRC_BIT,&bc);VkMemoryRequirements req;vkGetBufferMemoryRequirements(dev,b,&req);
  VkMemoryOpaqueCaptureAddressAllocateInfo mc={.sType=VK_STRUCTURE_TYPE_MEMORY_OPAQUE_CAPTURE_ADDRESS_ALLOCATE_INFO,.opaqueCaptureAddress=opaque_memory};VkMemoryAllocateFlagsInfo mf={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_FLAGS_INFO,.pNext=&mc,.flags=VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT|VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_CAPTURE_REPLAY_BIT};VkDeviceMemory m=alloc(req.size,type(req.memoryTypeBits,0),&mf);CHECK(vkBindBufferMemory(dev,b,m,0));
  VkBufferDeviceAddressInfo ba={.sType=VK_STRUCTURE_TYPE_BUFFER_DEVICE_ADDRESS_INFO,.buffer=b};VkDeviceMemoryOpaqueCaptureAddressInfo ma={.sType=VK_STRUCTURE_TYPE_DEVICE_MEMORY_OPAQUE_CAPTURE_ADDRESS_INFO,.memory=m};uint64_t ob=vkGetBufferOpaqueCaptureAddress(dev,&ba),om=vkGetDeviceMemoryOpaqueCaptureAddress(dev,&ma),da=vkGetBufferDeviceAddress(dev,&ba);
  if((replay||capture_input)&&(ob!=opaque_buffer||om!=opaque_memory||da!=device_address)){fprintf(stderr,"Capture/replay address mismatch\n");return 8;}opaque_buffer=ob;opaque_memory=om;device_address=da;
  if(!replay&&capture_output){FILE *f=fopen(capture_output,"w");if(!f)return 9;fprintf(f,"%" PRIu64 " %" PRIu64 " %" PRIu64 "\n",ob,om,da);if(fclose(f))return 9;}
  CHECK(vkResetCommandBuffer(cmd,0));VkCommandBufferBeginInfo cb={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};CHECK(vkBeginCommandBuffer(cmd,&cb));vkCmdFillBuffer(cmd,b,0,VK_WHOLE_SIZE,0xabcdef12);
  VkBufferMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT,.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.buffer=b,.size=VK_WHOLE_SIZE};vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,NULL,1,&barrier,0,NULL);VkBufferCopy copy={0,0,69632};vkCmdCopyBuffer(cmd,b,cr,1,&copy);barrier.buffer=cr;barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,NULL,1,&barrier,0,NULL);
  CHECK(vkEndCommandBuffer(cmd));VkSubmitInfo si={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.commandBufferCount=1,.pCommandBuffers=&cmd};CHECK(vkQueueSubmit(q,1,&si,fence));wait(fence);unsigned bad=0;for(unsigned i=0;i<69632/4;i++)if(mapped[i]!=0xabcdef12)bad++;printf("CAPTURE_REPLAY iteration=%u external=%u address_64k_aligned=%u mismatches=%u\n",replay,!!capture_input,!(da%65536),bad);if(bad)return 10;vkDestroyBuffer(dev,b,NULL);vkFreeMemory(dev,m,NULL);
 }
 vkUnmapMemory(dev,crm);vkDestroyBuffer(dev,cr,NULL);vkFreeMemory(dev,crm,NULL);
 CHECK(vkDeviceWaitIdle(dev));vkDestroySemaphore(dev,bound,NULL);vkDestroyFence(dev,fence,NULL);vkDestroyCommandPool(dev,pool,NULL);vkDestroyDevice(dev,NULL);vkDestroyInstance(in,NULL);printf("MEMORY_PASS sparse_remaps=%u capture_replay=1 unmap_after_fence=1\n",loops);return 0;
}
