#include "libipa/camera_sensor_helper.h"
#include <iostream>
using namespace libcamera::ipa;
int main()
{
    auto helper = CameraSensorHelperFactoryBase::create("s5kgw1");
    if (!helper) return 3;
    if (helper->blackLevel().has_value()) return 4;
    for (unsigned int code = 32; code <= 1024; ++code) {
        double gain = helper->gain(code);
        if (gain != double(code) / 32 || helper->gainCode(gain) != code) return 5;
        if (code < 1024 && helper->gain(code + 1) - gain != 1.0 / 32) return 6;
    }
    auto front = CameraSensorHelperFactoryBase::create("imx471");
    auto rear = CameraSensorHelperFactoryBase::create("imx319");
    auto tele = CameraSensorHelperFactoryBase::create("s5k3m5");
    if (!front || !rear || !tele || front->gainCode(2) != 512 ||
        rear->gainCode(2) != 512 || tele->gainCode(1.5) != 48) return 7;
    if (helper->gainCode(1.03125) != 33 || helper->gainCode(32) != 1024) return 8;
    std::cout << "{\"passed\":true,\"native_codes_round_tripped\":993,\"other_three_helpers_preserved\":true,\"black_level_not_assumed\":true}\n";
    return 0;
}
