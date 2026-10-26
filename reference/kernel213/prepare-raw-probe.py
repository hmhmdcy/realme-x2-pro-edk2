from pathlib import Path
here=Path(__file__).resolve().parent
text=(here/'isp-pattern-probe.cpp').read_text()
text=text.replace('#include <algorithm>', '#include <algorithm>\n#include <array>')
text=text.replace('const char *path)', 'const char *path, int selected)')
text=text.replace('control.value = 2;', 'control.value = selected;').replace('control.value == 2,', 'control.value == selected,')
text=text.replace('    bool allZero;\n', '''    bool allZero;
    unsigned int occupiedBins;
    double belowBlack64Fraction;
    double changedFraction;
    std::array<double, 4> bayerMean;
    std::array<double, 8> horizontalMean;
''')
text=text.replace('explicit Capture(std::shared_ptr<Camera> camera) : camera_(camera) {}', '''Capture(std::shared_ptr<Camera> camera, bool raw, const StreamConfiguration &cfg)
        : camera_(camera), raw_(raw), width_(cfg.size.width), height_(cfg.size.height), stride_(cfg.stride) {}''')
text=text.replace('''        uint64_t sum = 0, sumSquares = 0;''', '''        std::vector<uint16_t> active;
        if (raw_) {
            if (width_ != 1928 || height_ != 1088 || stride_ != 2416 || bytes != stride_ * height_) {
                munmap(mapping, plane.offset + plane.length);
                std::lock_guard<std::mutex> lock(mutex_);
                failed_ = true;
                ready_.notify_all();
                return;
            }
            active.reserve(width_ * height_);
            for (unsigned int row = 0; row < height_; ++row) {
                const uint8_t *line = pixels + row * stride_;
                for (unsigned int column = 0; column < width_ * 5 / 4; column += 5) {
                    const unsigned int lowBits = line[column + 4];
                    for (unsigned int index = 0; index < 4; ++index)
                        active.push_back((unsigned(line[column + index]) << 2) | ((lowBits >> (index * 2)) & 3));
                }
            }
        } else {
            active.assign(pixels, pixels + bytes);
        }
        uint64_t sum = 0, sumSquares = 0;''')
start=text.index('        unsigned int low = 255, high = 0;')
end=text.index('        bool again;',start)
text=text[:start]+'''        unsigned int low = raw_ ? 1023 : 255, high = 0;
        std::array<uint64_t, 1024> histogram{};
        std::array<uint64_t, 4> channelSum{}, channelCount{};
        std::array<uint64_t, 8> segmentSum{}, segmentCount{};
        size_t changed = 0, belowBlack = 0;
        for (size_t index = 0; index < active.size(); ++index) {
            const unsigned int value = active[index];
            sum += value;
            sumSquares += value * value;
            low = std::min(low, value);
            high = std::max(high, value);
            ++histogram[value];
            belowBlack += value < 64;
            if (previous_.size() == active.size())
                changed += previous_[index] != value;
            if (raw_) {
                const unsigned int column = index % width_, row = index / width_;
                const unsigned int channel = (row % 2) * 2 + column % 2;
                channelSum[channel] += value;
                ++channelCount[channel];
                const unsigned int segment = column * 8 / width_;
                segmentSum[segment] += value;
                ++segmentCount[segment];
            }
        }
        munmap(mapping, plane.offset + plane.length);
        const double mean = double(sum) / active.size();
        FrameStats stats{meta.sequence, low, high, mean,
                         std::sqrt(std::max(0.0, double(sumSquares) / active.size() - mean * mean)),
                         high == 0, unsigned(std::count_if(histogram.begin(), histogram.end(), [](uint64_t n) { return n != 0; })),
                         double(belowBlack) / active.size(), previous_.size() == active.size() ? double(changed) / active.size() : -1.0,
                         {}, {}};
        for (unsigned int index = 0; index < 4; ++index)
            stats.bayerMean[index] = channelCount[index] ? double(channelSum[index]) / channelCount[index] : 0.0;
        for (unsigned int index = 0; index < 8; ++index)
            stats.horizontalMean[index] = segmentCount[index] ? double(segmentSum[index]) / segmentCount[index] : 0.0;
        previous_ = std::move(active);
''' + text[end:]
text=text.replace('''        std::cout << "{\\"sensor_internal_pattern\\":2,\\"ambient_independent\\":true,\\"frames\\":[";''', '''        std::cout << "{\\"raw\\":" << (raw_ ? "true" : "false") << ",\\"width\\":" << width_ << ",\\"height\\":" << height_ << ",\\"stride\\":" << stride_ << ",\\"frames\\":[";''')
text=text.replace('''                      << ",\\"all_zero\\":" << (frame.allZero ? "true" : "false") << '}';''', '''                      << ",\\"all_zero\\":" << (frame.allZero ? "true" : "false")
                      << ",\\"occupied_bins\\":" << frame.occupiedBins
                      << ",\\"below_black64_fraction\\":" << frame.belowBlack64Fraction
                      << ",\\"changed_fraction\\":" << frame.changedFraction
                      << ",\\"bayer_mean_rg_gb\\":[";
            for (unsigned int index = 0; index < 4; ++index) {
                if (index) std::cout << ',';
                std::cout << frame.bayerMean[index];
            }
            std::cout << "],\\"horizontal_eighth_means\\":[";
            for (unsigned int index = 0; index < 8; ++index) {
                if (index) std::cout << ',';
                std::cout << frame.horizontalMean[index];
            }
            std::cout << "]}";''')
text=text.replace('''    std::shared_ptr<Camera> camera_;
    std::mutex mutex_;''', '''    std::shared_ptr<Camera> camera_;
    bool raw_;
    unsigned int width_, height_, stride_;
    std::vector<uint16_t> previous_;
    std::mutex mutex_;''')
text=text.replace('''    if (argc != 2)
        return 2;''', '''    if (argc != 4 || (std::string(argv[2]) != "raw" && std::string(argv[2]) != "rgb") || (std::string(argv[3]) != "0" && std::string(argv[3]) != "2"))
        return 2;
    const bool raw = std::string(argv[2]) == "raw";
    const int selected = std::stoi(argv[3]);''')
text=text.replace('camera->generateConfiguration({StreamRole::Viewfinder})', 'camera->generateConfiguration({raw ? StreamRole::Raw : StreamRole::Viewfinder})')
text=text.replace('streamConfiguration.size = {1920, 1088};', 'streamConfiguration.size = {raw ? 1928U : 1920U, 1088};')
text=text.replace('streamConfiguration.pixelFormat = formats::RGB888;', 'streamConfiguration.pixelFormat = raw ? formats::SRGGB10_CSI2P : formats::RGB888;')
text=text.replace('streamConfiguration.pixelFormat == formats::RGB888,', 'streamConfiguration.pixelFormat == (raw ? formats::SRGGB10_CSI2P : formats::RGB888),')
text=text.replace('std::make_unique<PatternGuard>(argv[1])', 'std::make_unique<PatternGuard>(argv[1], selected)')
text=text.replace('std::make_unique<Capture>(camera)', 'std::make_unique<Capture>(camera, raw, streamConfiguration)')
text=text.replace('''    if (acquired)
        camera->release();
    manager.stop();''', '''    if (acquired)
        camera->release();
    capture.reset();
    camera.reset();
    manager.stop();''')
assert 'formats::SRGGB10_CSI2P' in text and 'active.reserve' in text and 'below_black64_fraction' in text
(here/'raw-dark-probe.cpp').write_text(text)
builder=(here/'build-pattern-probe.py').read_text().replace('isp-pattern-probe','raw-dark-probe').replace('camera213-pattern-probe','camera213-raw-dark-probe').replace('pattern-probe-build','raw-dark-probe-build').replace('compile-pattern-probe','compile-raw-dark-probe')
builder=builder.replace('ambient_independent_sensor_color_bar_probe_built=True','raw10_dark_statistics_probe_built=True').replace('restores_test_pattern_on_exit=True','restores_test_pattern_on_exit=True,excludes_six_padding_bytes_per_raw_row=True')
(here/'build-raw-dark-probe.py').write_text(builder)
