// Read cached EUD USB descriptors through libusb; never open/claim a device.
// Windows/MSYS2: g++ eud-usb-descriptors.cpp -lusb-1.0 -o eud-usb-descriptors.exe
#include <cstdio>
#include <libusb-1.0/libusb.h>

static void extra(const unsigned char *p, int n) {
    std::printf(" extra[%d]=", n);
    for (int i = 0; i < n; ++i) std::printf("%02x", p[i]);
    std::puts("");
}

int main() {
    libusb_context *ctx = nullptr;
    if (libusb_init(&ctx) != 0) return 1;
    libusb_device **list = nullptr;
    auto count = libusb_get_device_list(ctx, &list);
    bool found = false, success = false;
    for (ssize_t i = 0; i < count; ++i) {
        libusb_device_descriptor d{};
        if (libusb_get_device_descriptor(list[i], &d) != 0 ||
            d.idVendor != 0x05c6 || d.idProduct != 0x9505) continue;
        found = true;
        std::printf("bus=%u address=%u vid=%04x pid=%04x bcdDevice=%04x configurations=%u\n",
                    libusb_get_bus_number(list[i]), libusb_get_device_address(list[i]),
                    d.idVendor, d.idProduct, d.bcdDevice, d.bNumConfigurations);
        for (unsigned c = 0; c < d.bNumConfigurations; ++c) {
            libusb_config_descriptor *cfg = nullptr;
            int rc = libusb_get_config_descriptor(list[i], c, &cfg);
            if (rc) { std::printf("config_error=%s\n", libusb_error_name(rc)); continue; }
            success = true;
            std::printf("config=%u total_length=%u interfaces=%u", cfg->bConfigurationValue,
                        cfg->wTotalLength, cfg->bNumInterfaces);
            extra(cfg->extra, cfg->extra_length);
            for (unsigned n = 0; n < cfg->bNumInterfaces; ++n) {
                for (int a = 0; a < cfg->interface[n].num_altsetting; ++a) {
                    const auto &it = cfg->interface[n].altsetting[a];
                    std::printf("interface=%u alt=%u class=%02x subclass=%02x protocol=%02x endpoints=%u",
                                it.bInterfaceNumber, it.bAlternateSetting, it.bInterfaceClass,
                                it.bInterfaceSubClass, it.bInterfaceProtocol, it.bNumEndpoints);
                    extra(it.extra, it.extra_length);
                    for (unsigned e = 0; e < it.bNumEndpoints; ++e) {
                        const auto &ep = it.endpoint[e];
                        std::printf("ep=%02x attributes=%02x max_packet=%u interval=%u",
                                    ep.bEndpointAddress, ep.bmAttributes, ep.wMaxPacketSize, ep.bInterval);
                        extra(ep.extra, ep.extra_length);
                    }
                }
            }
            libusb_free_config_descriptor(cfg);
        }
    }
    libusb_free_device_list(list, 1);
    libusb_exit(ctx);
    if (!found) std::puts("EUD 9505 not found");
    return success ? 0 : 1;
}
