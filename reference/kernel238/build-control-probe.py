"""Extend the exact physical probe with four explicit control phases."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel238');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
text=(R.parent/'kernel237/native-physical-probe.cpp').read_text()
def replace(old,new):
 global text
 assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
replace('#include <vector>','#include <vector>\n#include <map>')
replace('    unsigned int sequence;','    unsigned int sequence;\n    unsigned int queuedIndex;\n    int exposure, exposureMode, gainMode;\n    float gain;\n    std::array<unsigned int, 3> quantiles;\n    double saturatedFraction;')
replace('    void completed(Request *request)\n', '''    static void manual(ControlList &list, unsigned int phase)
    {
        list.set(controls::AeEnable, false);
        list.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
        list.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
        list.set(controls::ExposureTime, phase == 0 || phase == 3 ? 2000 : 32000);
        list.set(controls::AnalogueGain, phase == 2 ? 8.0f : 1.0f);
    }
    int queue(Request *request)
    {
        {
            std::lock_guard lock(queueMutex_);
            if (nextQueued_ >= 48) return 0;
            requestIndex_[request] = nextQueued_++;
            manual(request->controls(), requestIndex_[request] / 12);
        }
        return camera_->queueRequest(request);
    }
    void completed(Request *request)
''')
replace('        catch (...) {\n            std::lock_guard<std::mutex> lock(mutex_);', '        catch (const std::exception &error) {\n            std::cerr << "ERROR: callback: " << error.what() << \'\\n\';\n            std::lock_guard<std::mutex> lock(mutex_);')
replace('        const auto &plane = buffer->planes()[0];', '''        unsigned int queuedIndex;
        { std::lock_guard lock(queueMutex_); queuedIndex = requestIndex_.at(request); }
        auto exposure = request->metadata().get(controls::ExposureTime);
        auto gain = request->metadata().get(controls::AnalogueGain);
        auto exposureMode = request->metadata().get(controls::ExposureTimeMode);
        auto gainMode = request->metadata().get(controls::AnalogueGainMode);
        require(exposure && gain && exposureMode && gainMode, "capture controls metadata present");
        require(*exposureMode == controls::ExposureTimeModeManual && *gainMode == controls::AnalogueGainModeManual, "both captured modes manual");
        if (queuedIndex % 12 >= 6) {
            unsigned int phase = queuedIndex / 12;
            int target = phase == 0 || phase == 3 ? 2000 : 32000;
            float targetGain = phase == 2 ? 8.0f : 1.0f;
            require(std::abs(*exposure - target) <= 20 && std::abs(*gain - targetGain) < 0.03f, "settled captured exposure and gain match targets");
        }
        const auto &plane = buffer->planes()[0];''')
replace('FrameStats stats{meta.sequence, meta.timestamp,', 'FrameStats stats{meta.sequence, queuedIndex, *exposure, *exposureMode, *gainMode, *gain, {}, double(histogram[1023]) / active.size(), meta.timestamp,')
replace('        previous_ = std::move(active);', '''        for (unsigned int q = 0; q < 3; ++q) {
            uint64_t cumulative = 0, wanted = (active.size() * (q == 0 ? 10 : q == 1 ? 50 : 90) + 99) / 100;
            for (unsigned int value = 0; value < histogram.size(); ++value) {
                cumulative += histogram[value];
                if (cumulative >= wanted) { stats.quantiles[q] = value; break; }
            }
        }
        previous_ = std::move(active);''')
text=text.replace('frames_.size() >= 6','frames_.size() >= 48').replace('frames_.size() < 6','frames_.size() < 48').replace('frames_.size() == 6','frames_.size() == 48').replace('std::chrono::seconds(10)','std::chrono::seconds(45)')
replace('            if (camera_->queueRequest(request) != 0)', '            if (queue(request) != 0)')
replace('                      << ",\\\"timestamp_ns\\\":" << frame.timestamp', '''                      << ",\\\"queued_index\\\":" << frame.queuedIndex
                      << ",\\\"phase\\\":" << frame.queuedIndex / 12
                      << ",\\\"settled\\\":" << (frame.queuedIndex % 12 >= 6 ? "true" : "false")
                      << ",\\\"exposure_us\\\":" << frame.exposure
                      << ",\\\"analogue_gain\\\":" << frame.gain
                      << ",\\\"exposure_mode\\\":" << frame.exposureMode
                      << ",\\\"gain_mode\\\":" << frame.gainMode
                      << ",\\\"quantiles_p10_p50_p90\\\":[" << frame.quantiles[0] << ',' << frame.quantiles[1] << ',' << frame.quantiles[2] << ']'
                      << ",\\\"saturated_fraction\\\":" << frame.saturatedFraction
                      << ",\\\"timestamp_ns\\\":" << frame.timestamp''')
replace('    Stream *stream_;','    Stream *stream_;\n    std::mutex queueMutex_;\n    std::map<Request *, unsigned int> requestIndex_;\n    unsigned int nextQueued_ = 0;')
replace('    if (!rear && !front) return 2;','    if (!rear || front) return 2;')
replace('        require(camera->start() == 0, "start physical capture");', '''        auto gainInfo = camera->controls().find(controls::AnalogueGain.id());
        require(gainInfo != camera->controls().end() && gainInfo->second.min().get<float>() == 1.0f && gainInfo->second.max().get<float>() == 16.0f && gainInfo->second.def().get<float>() == 1.0f, "IMX319 public gain range 1..16 default1");
        ControlList initial(camera->controls()); Capture::manual(initial, 0);
        require(camera->start(&initial) == 0, "start physical capture with explicit controls");''')
replace('            require(camera->queueRequest(request.get()) == 0, "queue initial request");','            require(capture->queue(request.get()) == 0, "queue initial controlled request");')
text=text.replace('wait for six successful frames','wait for 48 successful controlled frames')
source=R/'physical-control-probe.cpp';assert not source.exists();source.write_text(text);shutil.copyfile(source,SDK/'private/physical-control-probe238.cpp')
cmd=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate238-r14/usr/include/libcamera','/private/physical-control-probe238.cpp','-L/candidate238-r14/usr/lib','-Wl,-rpath-link,/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-o','/private/physical-control-probe238']
p=subprocess.run(cmd,capture_output=True,timeout=180);(P/'control-probe-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,'inspect private compiler receipt'
target=P/'physical-control-probe238';shutil.copyfile(SDK/'private/physical-control-probe238',target)
report=dict(stage=238,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),binary_bytes=target.stat().st_size,exact_rear_selector_retained=True,all_48_success_frames_require_control_metadata=True,four_phases_twelve_each_last_six_settled=True,explicit_start_and_every_queue_controls=True,no_pixels_saved=True,werror_clean=True)
(R/'control-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
