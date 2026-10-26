/* Actual-device Vulkan rasterization and readback; no window-system or CPU ICD. */
#include <vulkan/vulkan.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "shaders.h"
#define W 64
#define BYTES (W*W*4)
#define CHECK(x) do { VkResult e=(x); if(e!=VK_SUCCESS) { fprintf(stderr,"FAIL %s: %d\n",#x,e); exit(1); } } while(0)
static VkDevice device;
static VkPhysicalDeviceMemoryProperties memories;
static uint32_t memory_type(uint32_t bits, VkMemoryPropertyFlags flags) {
    for(uint32_t i=0;i<memories.memoryTypeCount;i++)
        if((bits&(1u<<i)) && (memories.memoryTypes[i].propertyFlags&flags)==flags) return i;
    fprintf(stderr,"FAIL compatible memory type\n"); exit(1);
}
static VkDeviceMemory allocation(VkMemoryRequirements req,VkMemoryPropertyFlags flags) {
    VkMemoryAllocateInfo a={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.allocationSize=req.size,.memoryTypeIndex=memory_type(req.memoryTypeBits,flags)};
    VkDeviceMemory m; CHECK(vkAllocateMemory(device,&a,NULL,&m)); return m;
}
static uint64_t ns(void) {struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
int main(int argc,char **argv) {
    unsigned loops=argc>1?strtoul(argv[1],NULL,10):12;
    if(loops<2 || loops>10000) return 2;
    VkApplicationInfo app={.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO,.pApplicationName="samurai-gpu-render",.apiVersion=VK_API_VERSION_1_2};
    VkInstanceCreateInfo ici={.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,.pApplicationInfo=&app};
    VkInstance instance; CHECK(vkCreateInstance(&ici,NULL,&instance));
    uint32_t count=0; CHECK(vkEnumeratePhysicalDevices(instance,&count,NULL));
    if(count!=1) {fprintf(stderr,"FAIL expected exactly one selected physical GPU, got %u\n",count);return 1;}
    VkPhysicalDevice physical; CHECK(vkEnumeratePhysicalDevices(instance,&count,&physical));
    VkPhysicalDeviceDriverProperties driver={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};
    VkPhysicalDeviceProperties2 props={.sType=VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2,.pNext=&driver};
    vkGetPhysicalDeviceProperties2(physical,&props);
    printf("device=%s vendor=%04x device_id=%08x driver=%s info=%s api=%u.%u.%u\n",props.properties.deviceName,props.properties.vendorID,props.properties.deviceID,driver.driverName,driver.driverInfo,VK_API_VERSION_MAJOR(props.properties.apiVersion),VK_API_VERSION_MINOR(props.properties.apiVersion),VK_API_VERSION_PATCH(props.properties.apiVersion));
    if(!strstr(props.properties.deviceName,"640") || driver.driverID!=VK_DRIVER_ID_MESA_TURNIP || props.properties.deviceType==VK_PHYSICAL_DEVICE_TYPE_CPU) {fprintf(stderr,"FAIL expected actual Turnip A640\n");return 1;}
    vkGetPhysicalDeviceMemoryProperties(physical,&memories);
    uint32_t n=0; vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,NULL);
    VkQueueFamilyProperties *families=calloc(n,sizeof(*families)); vkGetPhysicalDeviceQueueFamilyProperties(physical,&n,families);
    uint32_t family=UINT32_MAX; for(uint32_t i=0;i<n;i++) if(families[i].queueFlags&VK_QUEUE_GRAPHICS_BIT) {family=i;break;} free(families);
    if(family==UINT32_MAX) return 1;
    float priority=1.0;
    VkDeviceQueueCreateInfo qi={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
    VkDeviceCreateInfo di={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.queueCreateInfoCount=1,.pQueueCreateInfos=&qi}; CHECK(vkCreateDevice(physical,&di,NULL,&device));
    VkQueue queue; vkGetDeviceQueue(device,family,0,&queue);
    VkImageCreateInfo imci={.sType=VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,.imageType=VK_IMAGE_TYPE_2D,.format=VK_FORMAT_R8G8B8A8_UNORM,.extent={W,W,1},.mipLevels=1,.arrayLayers=1,.samples=VK_SAMPLE_COUNT_1_BIT,.tiling=VK_IMAGE_TILING_OPTIMAL,.usage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE,.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED};
    VkImage image; CHECK(vkCreateImage(device,&imci,NULL,&image));
    VkMemoryRequirements req; vkGetImageMemoryRequirements(device,image,&req); VkDeviceMemory imem=allocation(req,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT); CHECK(vkBindImageMemory(device,image,imem,0));
    VkImageViewCreateInfo vci={.sType=VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,.image=image,.viewType=VK_IMAGE_VIEW_TYPE_2D,.format=imci.format,.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1}};
    VkImageView view; CHECK(vkCreateImageView(device,&vci,NULL,&view));
    VkBufferCreateInfo bci={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,.size=BYTES,.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE};
    VkBuffer buffer; CHECK(vkCreateBuffer(device,&bci,NULL,&buffer)); vkGetBufferMemoryRequirements(device,buffer,&req);
    VkDeviceMemory bmem=allocation(req,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT); CHECK(vkBindBufferMemory(device,buffer,bmem,0));
    uint8_t *pixels; CHECK(vkMapMemory(device,bmem,0,BYTES,0,(void**)&pixels));
    VkAttachmentDescription attachment={.format=imci.format,.samples=VK_SAMPLE_COUNT_1_BIT,.loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR,.storeOp=VK_ATTACHMENT_STORE_OP_STORE,.stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE,.stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE,.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED,.finalLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL};
    VkAttachmentReference ar={0,VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL};
    VkSubpassDescription sub={.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS,.colorAttachmentCount=1,.pColorAttachments=&ar};
    VkSubpassDependency dep[2]={{.srcSubpass=VK_SUBPASS_EXTERNAL,.dstSubpass=0,.srcStageMask=VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,.dstStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,.dstAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT},{.srcSubpass=0,.dstSubpass=VK_SUBPASS_EXTERNAL,.srcStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,.dstStageMask=VK_PIPELINE_STAGE_TRANSFER_BIT,.srcAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT}};
    VkRenderPassCreateInfo rpci={.sType=VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,.attachmentCount=1,.pAttachments=&attachment,.subpassCount=1,.pSubpasses=&sub,.dependencyCount=2,.pDependencies=dep};
    VkRenderPass pass; CHECK(vkCreateRenderPass(device,&rpci,NULL,&pass));
    VkFramebufferCreateInfo fbci={.sType=VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO,.renderPass=pass,.attachmentCount=1,.pAttachments=&view,.width=W,.height=W,.layers=1};
    VkFramebuffer framebuffer; CHECK(vkCreateFramebuffer(device,&fbci,NULL,&framebuffer));
    VkShaderModuleCreateInfo smci={.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,.codeSize=sizeof(vertex_spv),.pCode=vertex_spv};
    VkShaderModule vs,fs; CHECK(vkCreateShaderModule(device,&smci,NULL,&vs)); smci.codeSize=sizeof(fragment_spv);smci.pCode=fragment_spv; CHECK(vkCreateShaderModule(device,&smci,NULL,&fs));
    VkPipelineShaderStageCreateInfo stages[2]={{.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,.stage=VK_SHADER_STAGE_VERTEX_BIT,.module=vs,.pName="main"},{.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,.stage=VK_SHADER_STAGE_FRAGMENT_BIT,.module=fs,.pName="main"}};
    VkPushConstantRange push={VK_SHADER_STAGE_FRAGMENT_BIT,0,16};
    VkPipelineLayoutCreateInfo plci={.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,.pushConstantRangeCount=1,.pPushConstantRanges=&push}; VkPipelineLayout layout; CHECK(vkCreatePipelineLayout(device,&plci,NULL,&layout));
    VkPipelineVertexInputStateCreateInfo vi={.sType=VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
    VkPipelineInputAssemblyStateCreateInfo ia={.sType=VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST};
    VkViewport vp={0,0,W,W,0,1}; VkRect2D sc={{0,0},{W,W}};
    VkPipelineViewportStateCreateInfo vpci={.sType=VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,.viewportCount=1,.pViewports=&vp,.scissorCount=1,.pScissors=&sc};
    VkPipelineRasterizationStateCreateInfo raster={.sType=VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,.polygonMode=VK_POLYGON_MODE_FILL,.cullMode=VK_CULL_MODE_NONE,.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE,.lineWidth=1};
    VkPipelineMultisampleStateCreateInfo sample={.sType=VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT};
    VkPipelineColorBlendAttachmentState blend={.colorWriteMask=15}; VkPipelineColorBlendStateCreateInfo blending={.sType=VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,.attachmentCount=1,.pAttachments=&blend};
    VkGraphicsPipelineCreateInfo pci={.sType=VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,.stageCount=2,.pStages=stages,.pVertexInputState=&vi,.pInputAssemblyState=&ia,.pViewportState=&vpci,.pRasterizationState=&raster,.pMultisampleState=&sample,.pColorBlendState=&blending,.layout=layout,.renderPass=pass};
    VkPipeline pipeline; CHECK(vkCreateGraphicsPipelines(device,VK_NULL_HANDLE,1,&pci,NULL,&pipeline));
    VkCommandPoolCreateInfo cpci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,.queueFamilyIndex=family};
    VkCommandPool pool; CHECK(vkCreateCommandPool(device,&cpci,NULL,&pool)); VkCommandBufferAllocateInfo cai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=pool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1}; VkCommandBuffer cmd; CHECK(vkAllocateCommandBuffers(device,&cai,&cmd));
    VkFenceCreateInfo fci={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO}; VkFence fence; CHECK(vkCreateFence(device,&fci,NULL,&fence));
    uint32_t hash[2]={0},colored_expected=0; uint64_t begin=ns();
    for(unsigned iteration=0;iteration<loops;iteration++) {
        memset(pixels,0xa5,BYTES); CHECK(vkResetCommandBuffer(cmd,0)); CHECK(vkResetFences(device,1,&fence));
        VkCommandBufferBeginInfo begin_info={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT}; CHECK(vkBeginCommandBuffer(cmd,&begin_info));
        VkClearValue clear={.color={{0,0,1,1}}}; VkRenderPassBeginInfo rb={.sType=VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,.renderPass=pass,.framebuffer=framebuffer,.renderArea={{0,0},{W,W}},.clearValueCount=1,.pClearValues=&clear};
        vkCmdBeginRenderPass(cmd,&rb,VK_SUBPASS_CONTENTS_INLINE);vkCmdBindPipeline(cmd,VK_PIPELINE_BIND_POINT_GRAPHICS,pipeline);
        float color[4]={iteration%2?0:1,iteration%2?1:0,0,1}; vkCmdPushConstants(cmd,layout,VK_SHADER_STAGE_FRAGMENT_BIT,0,16,color); vkCmdDraw(cmd,3,1,0,0);vkCmdEndRenderPass(cmd);
        VkBufferImageCopy copy={.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1},.imageExtent={W,W,1}};
        vkCmdCopyImageToBuffer(cmd,image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,buffer,1,&copy);
        VkBufferMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT,.dstAccessMask=VK_ACCESS_HOST_READ_BIT,.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED,.buffer=buffer,.offset=0,.size=BYTES};
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,0,NULL,1,&barrier,0,NULL); CHECK(vkEndCommandBuffer(cmd));
        VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.commandBufferCount=1,.pCommandBuffers=&cmd}; CHECK(vkQueueSubmit(queue,1,&submit,fence)); CHECK(vkWaitForFences(device,1,&fence,VK_TRUE,5000000000ull));
        uint8_t want[4]={iteration%2?0:255,iteration%2?255:0,0,255},blue[4]={0,0,255,255}; uint32_t colored=0,h=2166136261u;
        for(unsigned i=0;i<BYTES;i++) h=(h^pixels[i])*16777619u;
        for(unsigned p=0;p<W*W;p++) {if(!memcmp(pixels+4*p,want,4)) colored++; else if(memcmp(pixels+4*p,blue,4)) {fprintf(stderr,"FAIL unexpected pixel %u: %u,%u,%u,%u\n",p,pixels[p*4],pixels[p*4+1],pixels[p*4+2],pixels[p*4+3]);return 1;}}
        if(colored<1000 || colored>1600 || memcmp(pixels+4*(W*32+32),want,4) || memcmp(pixels,blue,4) || (colored_expected && colored!=colored_expected) || (iteration>=2 && hash[iteration%2]!=h)) {fprintf(stderr,"FAIL triangle geometry or repeated readback\n");return 1;}
        hash[iteration%2]=h; colored_expected=colored;
        if(iteration<4 || iteration==loops-1) printf("frame=%u color=%s triangle_pixels=%u background_pixels=%u fnv1a=%08x fence=signaled readback=PASS\n",iteration,iteration%2?"green":"red",colored,W*W-colored,h);
        if(iteration==0 && argc>2) {FILE *f=fopen(argv[2],"wb"); if(!f) return 1;fprintf(f,"P6\n%d %d\n255\n",W,W); for(unsigned p=0;p<W*W;p++) fwrite(pixels+4*p,1,3,f);fclose(f);}
    }
    CHECK(vkDeviceWaitIdle(device));
    printf("PASS real A640 vertex/fragment rasterization: %u submissions, alternating readbacks=%08x/%08x elapsed_ms=%.3f\n",loops,hash[0],hash[1],(ns()-begin)/1e6);
    vkDestroyFence(device,fence,NULL);vkDestroyCommandPool(device,pool,NULL);vkDestroyPipeline(device,pipeline,NULL);vkDestroyPipelineLayout(device,layout,NULL);vkDestroyShaderModule(device,vs,NULL);vkDestroyShaderModule(device,fs,NULL);vkDestroyFramebuffer(device,framebuffer,NULL);vkDestroyRenderPass(device,pass,NULL);vkDestroyImageView(device,view,NULL);vkDestroyImage(device,image,NULL);vkFreeMemory(device,imem,NULL);vkUnmapMemory(device,bmem);vkDestroyBuffer(device,buffer,NULL);vkFreeMemory(device,bmem,NULL);vkDestroyDevice(device,NULL);vkDestroyInstance(instance,NULL);return 0;
}
