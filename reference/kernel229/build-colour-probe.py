"""Extend the established RAM-only probe with channel and 32-frame AE statistics."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import time

ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel229')
sdk = Path('/home/cy122/x2pro-linux/libcamera214-root')
text = (ref.parent / 'kernel219/native-mode-probe.cpp').read_text()


def replace(old, new):
    global text
    assert text.count(old) == 1, old[:100]
    text = text.replace(old, new, 1)


replace('    std::array<double, 8> horizontalMean;', '''    std::array<double, 8> horizontalMean;
    std::array<double, 3> byteChannelMean{};
    std::array<double, 3> byteChannelStddev{};
    std::array<unsigned int, 3> byteChannelMin{};
    std::array<unsigned int, 3> byteChannelMax{};
    double differingChannelsFraction = -1.0;
    double clippedPixelsFraction = -1.0;
    int exposureUs = -1;
    float analogueGain = -1.0f;''')
replace('if (buffer->planes().empty() || meta.planes().empty())',
        'if (meta.status != FrameMetadata::FrameSuccess || buffer->planes().empty() || meta.planes().empty())')
replace('''        } else {
            active.assign(pixels, pixels + bytes);
        }''', '''        } else {
            if (stride_ < width_ * 3 || bytes != size_t(stride_) * height_) {
                munmap(mapping, plane.offset + plane.length);
                std::lock_guard<std::mutex> lock(mutex_);
                failed_ = true;
                ready_.notify_all();
                return;
            }
            active.reserve(size_t(width_) * height_ * 3);
            for (unsigned int row = 0; row < height_; ++row)
                active.insert(active.end(), pixels + row * stride_, pixels + row * stride_ + width_ * 3);
        }''')
replace('        size_t changed = 0, belowBlack = 0;', '''        size_t changed = 0, belowBlack = 0;
        std::array<uint64_t, 3> rgbSum{}, rgbSquares{}, rgbCount{};
        std::array<unsigned int, 3> rgbMin{255, 255, 255}, rgbMax{};
        size_t differing = 0, clipped = 0;''')
marker='''            if (raw_) {
                const unsigned int column = index % width_, row = index / width_;'''
replace(marker, '''            if (!raw_) {
                const unsigned int channel = index % 3;
                rgbSum[channel] += value;
                rgbSquares[channel] += value * value;
                ++rgbCount[channel];
                rgbMin[channel] = std::min(rgbMin[channel], value);
                rgbMax[channel] = std::max(rgbMax[channel], value);
                if (channel == 0) {
                    const auto lo = std::min({active[index], active[index + 1], active[index + 2]});
                    const auto hi = std::max({active[index], active[index + 1], active[index + 2]});
                    differing += hi >= 24 && hi - lo >= 12;
                    clipped += hi >= 250;
                }
            }
''' + marker)
replace('        previous_ = std::move(active);', '''        if (!raw_) {
            for (unsigned int channel = 0; channel < 3; ++channel) {
                const double m = double(rgbSum[channel]) / rgbCount[channel];
                stats.byteChannelMean[channel] = m;
                stats.byteChannelStddev[channel] = std::sqrt(std::max(0.0, double(rgbSquares[channel]) / rgbCount[channel] - m * m));
                stats.byteChannelMin[channel] = rgbMin[channel];
                stats.byteChannelMax[channel] = rgbMax[channel];
            }
            stats.differingChannelsFraction = double(differing) / (size_t(width_) * height_);
            stats.clippedPixelsFraction = double(clipped) / (size_t(width_) * height_);
        }
        stats.exposureUs = request->metadata().get(controls::ExposureTime).value_or(-1);
        stats.analogueGain = request->metadata().get(controls::AnalogueGain).value_or(-1.0f);
        previous_ = std::move(active);''')
assert text.count('frames_.size() >= 6') == 1 and text.count('frames_.size() < 6') == 1 and text.count('frames_.size() == 6') == 1
text = text.replace('frames_.size() >= 6', 'frames_.size() >= 32').replace('frames_.size() < 6', 'frames_.size() < 32').replace('frames_.size() == 6', 'frames_.size() == 32')
text = text.replace('std::chrono::seconds(10)', 'std::chrono::seconds(35)').replace('wait for six frames', 'wait for 32 frames')
replace('            std::cout << "]}";', '''            std::cout << "],\\"byte_channel_means_012\\":[";
            for (unsigned int channel = 0; channel < 3; ++channel) {
                if (channel) std::cout << ',';
                std::cout << frame.byteChannelMean[channel];
            }
            std::cout << "],\\"byte_channel_stddevs_012\\":[";
            for (unsigned int channel = 0; channel < 3; ++channel) {
                if (channel) std::cout << ',';
                std::cout << frame.byteChannelStddev[channel];
            }
            std::cout << "],\\"byte_channel_mins_012\\":[";
            for (unsigned int channel = 0; channel < 3; ++channel) {
                if (channel) std::cout << ',';
                std::cout << frame.byteChannelMin[channel];
            }
            std::cout << "],\\"byte_channel_maxs_012\\":[";
            for (unsigned int channel = 0; channel < 3; ++channel) {
                if (channel) std::cout << ',';
                std::cout << frame.byteChannelMax[channel];
            }
            std::cout << "],\\"differing_channels_fraction\\":" << frame.differingChannelsFraction
                      << ",\\"clipped_pixels_fraction\\":" << frame.clippedPixelsFraction
                      << ",\\"exposure_us\\":" << frame.exposureUs
                      << ",\\"analogue_gain\\":" << frame.analogueGain << "}";''')
source = ref / 'daylight-colour-probe.cpp'
assert not source.exists()
source.write_text(text)
copy = sdk / 'private/daylight-colour-probe229.cpp'
assert not copy.exists()
shutil.copyfile(source, copy)
started = time.monotonic()
command = ['chroot', str(sdk), '/usr/bin/g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread',
           '-I/candidate/usr/include/libcamera', '/private/daylight-colour-probe229.cpp', '-L/candidate/usr/lib',
           '-Wl,-rpath-link,/candidate/usr/lib', '-lcamera', '-lcamera-base', '-o', '/private/daylight-colour-probe229']
result = subprocess.run(command, capture_output=True, timeout=150)
(private / 'colour-probe-build-private.log').write_bytes(result.stdout + result.stderr)
assert result.returncode == 0, 'Inspect the retained compiler diagnostic'
target = private / 'daylight-colour-probe229'
assert not target.exists()
shutil.copyfile(sdk / 'private/daylight-colour-probe229', target)
report = dict(stage=229, source_sha256=hashlib.sha256(text.encode()).hexdigest(),
              binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), binary_bytes=target.stat().st_size,
              build_seconds=round(time.monotonic() - started, 3), frames=32, no_pixel_files=True,
              rgb_row_padding_excluded=True, metadata_exposure_gain_recorded=True,
              channel_order_reported_as_memory_bytes_until_verified=True, full_sdk_not_rebuilt=True)
(ref / 'colour-probe-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
