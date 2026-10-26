/* Limited ARM64 SDK checks. CameraManager is never started; no device I/O. */
#include <cassert>
#include <dlfcn.h>
#include <iostream>
#include <string>
#include <unistd.h>

#include <libcamera/camera_manager.h>
#include <libcamera/base/file.h>
#include <libcamera/base/span.h>
#include "libcamera/internal/camera_sensor_properties.h"
#include "libcamera/internal/global_configuration.h"
#include "libcamera/internal/ipa_manager.h"
#include "libcamera/internal/ipa_module.h"
#include "libcamera/internal/ipa_proxy.h"
#include "libcamera/internal/source_paths.h"
#include "libcamera/internal/v4l2_subdevice.h"

using namespace libcamera;

struct PathProbe final : IPAProxy {
	using IPAProxy::IPAProxy;
	using IPAProxy::resolvePath;
};

int main(int argc, char **argv)
{
	assert(argc == 2 && getuid() == 10000 && geteuid() == 10000);
	assert(utils::libcameraBuildPath().empty());
	assert(utils::libcameraSourcePath().empty());
	Dl_info loaded{};
	assert(dladdr(reinterpret_cast<void *>(CameraSensorProperties::get), &loaded));
	assert(std::string(loaded.dli_fname) == "/usr/lib/libcamera.so.0.7");
	for (const auto &[name, cell] : { std::pair{"s5kgw1", 800U},
					std::pair{"imx319", 1400U},
					std::pair{"s5k3m5", 1000U},
					std::pair{"imx471", 1000U} }) {
		const auto *properties = CameraSensorProperties::get(name);
		assert(properties && properties->unitCellSize == Size(cell, cell));
		assert(properties->testPatternModes.at(controls::draft::TestPatternModeOff) == 0);
		if (std::string(name) == "s5kgw1") {
			assert(properties->testPatternModes.at(controls::draft::TestPatternModeColorBars) == 1);
			assert(properties->testPatternModes.size() == 2);
		}
	}
	const auto &format = MediaBusFormatInfo::info(0x2027);
	assert(format.code == 0x2027 && format.bitsPerPixel == 15);
	assert(format.colourEncoding == PixelFormatInfo::ColourEncodingYUV);
	GlobalConfiguration configuration;
	const std::string expected(argv[1]);
	auto value = configuration.option<std::string>({"kernel489_probe"});
	if (expected == "blocked") {
		assert(!value && configuration.version() == 1);
	} else {
		assert(value == expected && configuration.version() == 1);
	}
	IPAModule module("/usr/lib/libcamera/ipa/ipa_camss_vfe.so");
	assert(module.isValid());
	File file{module.path()};
	assert(file.open(File::OpenModeFlag::ReadOnly));
	Span<uint8_t> data = file.map();
	assert(!data.empty() && IPAManager::pubKey().verify(data, module.signature()));
	CameraManager manager;
	PathProbe proxy(&module, manager);
	assert(proxy.configurationFile("s5kgw1.yaml") == "/etc/libcamera/ipa/camss-vfe/s5kgw1.yaml");
	assert(proxy.resolvePath("camss_ipa_proxy") == "/usr/libexec/libcamera/camss_ipa_proxy");
	std::cout << "uid=10000 config=" << expected
		  << " installed_paths=1 properties=4 bus_2027_yuv15=1 signature=1"
		  << " system_profile_resolved=1 system_worker_resolved=1 manager_started=0\n";
}
