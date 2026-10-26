/* SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <vulkan/vulkan.h>

int main(void)
{
    VkInstance instance;
    VkApplicationInfo app = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
        .apiVersion = VK_API_VERSION_1_2 };
    VkInstanceCreateInfo create = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        .pApplicationInfo = &app };
    VkResult rc = vkCreateInstance(&create, NULL, &instance);
    if (rc) return 1;
    uint32_t count = 1;
    VkPhysicalDevice physical;
    rc = vkEnumeratePhysicalDevices(instance, &count, &physical);
    if (rc || count != 1) { vkDestroyInstance(instance, NULL); return 2; }
    VkPhysicalDeviceVulkan12Features v12 = {
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES };
    VkPhysicalDeviceFeatures2 features = {
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2, .pNext = &v12 };
    vkGetPhysicalDeviceFeatures2(physical, &features);
    VkPhysicalDeviceProperties properties;
    vkGetPhysicalDeviceProperties(physical, &properties);
    printf("{\"device\":\"%s\",\"sparseBinding\":%u,\"sparseResidencyBuffer\":%u,"
           "\"bufferDeviceAddress\":%u,\"bufferDeviceAddressCaptureReplay\":%u}\n",
        properties.deviceName, features.features.sparseBinding,
        features.features.sparseResidencyBuffer, v12.bufferDeviceAddress,
        v12.bufferDeviceAddressCaptureReplay);
    vkDestroyInstance(instance, NULL);
    return 0;
}
