"""Use actual threaded/isolated proxies for a subset of the module contract."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
s = (HERE / 'ipa-contract.cpp').read_text()
s = s.replace('#include <deque>', '''#include <deque>
#include <libcamera/camera_manager.h>
#include <libcamera/base/object.h>
#include <libcamera/base/thread.h>
#include <libcamera/base/event_dispatcher.h>
#include <libcamera/base/timer.h>
#include "libcamera/internal/ipa_module.h"
#include <libcamera/ipa/camss_ipa_proxy.h>''')
s = s.replace('struct Observation {', 'struct Observation : public Object {')
s = s.replace('{ ++calls; statistics = s; metadata = m; }',
              '{ ++calls; statistics = s; metadata = m; Thread::current()->eventDispatcher()->interrupt(); }')
start = s.index('\tvoid *handle = dlopen')
end = s.index('\tObservation observation;', start)
s = s[:start] + ''' CameraManager manager;
 IPAModule module(argv[1]); assert(module.isValid());
 std::unique_ptr<ipa::camss::IPACamssInterface> ipa;
 std::unique_ptr<ipa::camss::IPAProxyCamss> proxy;
 if (std::string(argv[2]) == "isolated") proxy = std::make_unique<ipa::camss::IPAProxyCamssIsolated>(&module, manager);
 else proxy = std::make_unique<ipa::camss::IPAProxyCamssThreaded>(&module, manager);
 assert(proxy->isValid());
 ipa.reset(proxy.release());
''' + s[end:]
start = s.index(' assert(ipa->configure(info, info.outputSize, sensorInfo, argv[2]')
end = s.index(' ControlList sensorOutput', start)
s = s[:start] + ''' assert(ipa->configure(info, info.outputSize, sensorInfo, argv[3], &ipaControls, &configuration) == 0);
 assert(configuration.enabled && configuration.exposureDelay == 2);
''' + s[end:]
start = s.index('\tIPABuffer conflict(')
end = s.index(' unsigned int proposals = 0', start)
s = s[:start] + ''' assert(ipa->mapBuffers({p}, {s}) == 0);
 ControlList controls(libcamera::controls::controls);
 controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeAuto);
 controls.set(controls::AnalogueGainMode, controls::AnalogueGainModeAuto);
 controls.set(controls::ExposureTime, int32_t(5000)); controls.set(controls::AnalogueGain, 2.0f);
 assert(start(3, controls) == 0);
 ipa::camss::SensorContext actual{true, 503, 512, UINT32_MAX};
 constexpr uint32_t statsBytes = sizeof(v4l2_isp_buffer) + sizeof(camss_stats_bhist);
 auto *envelope = static_cast<v4l2_isp_buffer *>(stats);
 auto *histogram = reinterpret_cast<camss_stats_bhist *>(static_cast<uint8_t *>(stats) + sizeof(*envelope));
 std::memset(stats, 0, 8192);
 envelope->version = V4L2_ISP_VERSION_V1; envelope->data_size = sizeof(*histogram);
 histogram->header.type = CAMSS_STATS_AEC_BHIST; histogram->header.size = sizeof(*histogram);
 histogram->bins[512] = 499392;
 auto callStats = [&](uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytes, const ipa::camss::SensorContext &context) {
  unsigned int before = observation.calls;
  ipa->processStats(epoch, sof, id, bytes, context);
  Timer deadline; deadline.start(std::chrono::milliseconds(2000));
  while (observation.calls == before && deadline.isRunning()) Thread::current()->eventDispatcher()->processEvents();
  deadline.stop();
  assert(observation.calls == before + 1);
 };
 callStats(3, 0, 100, statsBytes, actual);
 assert(!observation.statistics.status && !observation.statistics.automaticUpdate.valid);
 ipa->parametersApplied(3, 1);
 callStats(3, 1, 100, statsBytes, ipa::camss::SensorContext{});
 assert(!observation.statistics.automaticUpdate.valid);
''' + s[end:]
s = s.replace('ipa->processStats(', 'callStats(')
# The wrapper itself must call the proxy.
s = s.replace('  callStats(epoch, sof, id, bytes, context);', '  ipa->processStats(epoch, sof, id, bytes, context);')
start = s.index(' ipa->stop();\n callStats(3, 723')
end = s.index(' assert(start(4, controls)', start)
s = s[:start] + ' ipa->stop();\n' + s[end:]
s = s.replace('assert(ipaControls.at(&controls::ExposureTimeMode).values().size() == 2);', '')
s = s.replace('\tipa.reset(); dlclose(handle);', '\tipa.reset();')
s = s.replace('"IPA_CONTRACT_PASS callbacks="', '"IPA_PROXY_CONTRACT_PASS callbacks="')
(HERE / 'ipa-proxy-contract.cpp').write_text(s)
print('Prepared actual threaded / isolated proxy contract')
