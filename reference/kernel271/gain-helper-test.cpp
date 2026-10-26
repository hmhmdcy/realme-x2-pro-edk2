#include "libipa/camera_sensor_helper.h"
#include <cmath>
#include <iostream>
using namespace libcamera::ipa;
int main()
{
    auto helper = CameraSensorHelperFactoryBase::create("s5k3m5");
    if (!helper) return 3;
    if (helper->blackLevel().has_value()) return 4;
    for (unsigned int code = 32; code <= 512; ++code) {
        const double gain = helper->gain(code);
        if (gain != double(code) / 32 || helper->gainCode(gain) != code) return 5;
        if (code < 512 && helper->gain(code + 1) - gain != 1.0 / 32) return 6;
    }
    if (helper->gainCode(1.03125) != 33 || helper->gainCode(1.5) != 48) return 7;
    auto front = CameraSensorHelperFactoryBase::create("imx471");
    auto rear = CameraSensorHelperFactoryBase::create("imx319");
    if (!front || !rear || front->gainCode(2) != 512 || rear->gainCode(2) != 512) return 8;
    std::cout << "{\"passed\":true,\"native_codes_round_tripped\":481,\"fractional_gain_step\":0.03125,\"other_sensors_preserved\":true,\"black_level_not_assumed\":true}\n";
    return 0;
}
