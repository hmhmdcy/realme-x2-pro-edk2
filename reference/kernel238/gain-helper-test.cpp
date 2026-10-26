#include "libipa/camera_sensor_helper.h"
#include <cmath>
#include <iostream>
#include <array>
using namespace libcamera::ipa;
int main()
{
    auto helper = CameraSensorHelperFactoryBase::create("imx319");
    if (!helper) return 3;
    if (helper->blackLevel().has_value() || CameraSensorHelperFactoryBase::create("imx319-other")) return 4;
    unsigned int quantizedBelow = 0;
    double previous = 0.0;
    for (unsigned int code = 0; code <= 960; ++code) {
        double gain = helper->gain(code);
        if (!std::isfinite(gain) || gain <= previous || gain < 1.0 || gain > 16.0) return 5;
        unsigned int roundtrip = helper->gainCode(gain);
        if (roundtrip > code || code - roundtrip > 1) return 6;
        quantizedBelow += roundtrip < code;
        previous = gain;
    }
    const std::array<double, 5> gains{1.0, 2.0, 4.0, 8.0, 16.0};
    const std::array<unsigned int, 5> codes{0, 512, 768, 896, 960};
    for (size_t i = 0; i < gains.size(); ++i)
        if (helper->gainCode(gains[i]) != codes[i] || helper->gain(codes[i]) != gains[i]) return 7;
    auto front = CameraSensorHelperFactoryBase::create("imx471");
    if (!front || front->gainCode(2.0) != 512 || front->blackLevel().value_or(-1) != 4096) return 8;
    std::cout << "{\"passed\":true,\"all_961_codes_monotonic_finite\":true,\"five_selected_gains_exact\":true,\"no_black_level_invented\":true,\"front_helper_preserved\":true,\"one_code_inverse_truncations\":" << quantizedBelow << "}\n";
    return 0;
}
