"""Build the RAM-only probe with an exact physical selector and frame status."""
from pathlib import Path
import hashlib,json,shutil,subprocess

R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel237')
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
text=(R.parent/'kernel219/native-mode-probe.cpp').read_text()
def replace(old,new):
 global text
 assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
replace('// Finite, ambient-independent test of the real sensor -> CAMSS -> CPU ISP path.\n// The sensor test-pattern control is restored by RAII, including error exits.',
 '// Finite physical-camera RAM statistics. No pixels are written to files/stdout.\n// Exact OF ID, Model and subdevice entity are checked before acquisition.')
replace('#include <iostream>','#include <iostream>\n#include <fstream>\n#include <filesystem>')
replace('    unsigned int sequence;','    unsigned int sequence;\n    uint64_t timestamp;\n    int64_t sensorTimestamp;')
replace('        if (request->status() == Request::RequestCancelled)\n            return;\n        const FrameBuffer *buffer = request->buffers().begin()->second;\n        const auto &meta = buffer->metadata();\n        if (buffer->planes().empty() || meta.planes().empty()) {',
 '''        if (request->status() == Request::RequestCancelled)
            return;
        if (request->status() != Request::RequestComplete || request->buffers().size() != 1) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true; ready_.notify_all(); return;
        }
        const FrameBuffer *buffer = request->buffers().begin()->second;
        const auto &meta = buffer->metadata();
        if (meta.status != FrameMetadata::FrameSuccess || buffer->planes().size() != 1 || meta.planes().size() != 1) {''')
replace('FrameStats stats{meta.sequence, low, high, mean,',
 'FrameStats stats{meta.sequence, meta.timestamp, request->metadata().get(controls::SensorTimestamp).value_or(-1), low, high, mean,')
replace('            frames_.push_back(stats);',
 '''            if (!frames_.empty() && (stats.sequence <= frames_.back().sequence || stats.timestamp <= frames_.back().timestamp)) {
                failed_ = true; ready_.notify_all(); return;
            }
            frames_.push_back(stats);''')
replace('                      << ",\\\"byte_min\\\":" << frame.minimum',
 '                      << ",\\\"timestamp_ns\\\":" << frame.timestamp\n                      << ",\\\"sensor_timestamp_ns\\\":" << frame.sensorTimestamp\n                      << ",\\\"byte_min\\\":" << frame.minimum')
replace('    if (argc != 7 || (std::string(argv[2]) != "raw" && std::string(argv[2]) != "rgb") || (std::string(argv[3]) != "0" && std::string(argv[3]) != "2"))',
 '    if (argc != 9 || (std::string(argv[5]) != "raw" && std::string(argv[5]) != "rgb"))')
replace('    const bool raw = std::string(argv[2]) == "raw";\n    const int selected = std::stoi(argv[3]);\n    const unsigned int wantedWidth = std::stoul(argv[4]);\n    const unsigned int wantedHeight = std::stoul(argv[5]);\n    const unsigned int cfaCell = std::stoul(argv[6]);',
 '''    const std::string expectedId = argv[2], expectedModel = argv[3], expectedEntity = argv[4];
    const bool rear = expectedId == "/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10" && expectedModel == "imx319" && expectedEntity == "imx319 7-0010";
    const bool front = expectedId == "/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10" && expectedModel == "imx471" && expectedEntity == "imx471 9-0010";
    if (!rear && !front) return 2;
    const bool raw = std::string(argv[5]) == "raw";
    const int selected = 0;
    const unsigned int wantedWidth = std::stoul(argv[6]);
    const unsigned int wantedHeight = std::stoul(argv[7]);
    const unsigned int cfaCell = std::stoul(argv[8]);''')
replace('        require(manager.start() == 0, "start camera manager");',
 '''        const auto node = std::filesystem::path(argv[1]).filename();
        require(std::string(argv[1]) == "/dev/" + node.string() && node.string().starts_with("v4l-subdev"), "sensor device path");
        std::ifstream entityFile(std::filesystem::path("/sys/class/video4linux") / node / "name");
        std::string entity; std::getline(entityFile, entity);
        require(entityFile.good() || entityFile.eof(), "read sensor entity");
        require(entity == expectedEntity, "exact sensor entity");
        const auto ofNode = std::filesystem::canonical(std::filesystem::path("/sys/class/video4linux") / node / "device/of_node");
        require(ofNode.string() == "/sys/firmware/devicetree" + expectedId, "exact sensor OF node");
        require(manager.start() == 0, "start camera manager");''')
replace('            if (candidate->id().find("cci@ac4b000") != std::string::npos) {\n                require(!camera, "unique physical front camera");\n                camera = candidate;\n            }',
 '''            if (candidate->id() == expectedId) {
                require(!camera, "unique exact physical camera");
                require(candidate->properties().get(properties::Model).value_or("") == expectedModel, "exact camera Model");
                camera = candidate;
            }''')
text=text.replace('front camera','physical camera').replace('start color bar capture','start physical capture')
replace('        require(capture->wait(), "wait for six frames");\n        camera->stop();\n        started = false;\n        camera->requestCompleted.disconnect(capture.get());\n        pattern.reset();\n        capture->print();\n        status = 0;',
 '''        const bool complete = capture->wait();
        require(camera->stop() == 0, "stop physical camera");
        started = false;
        camera->requestCompleted.disconnect(capture.get());
        pattern.reset();
        capture->print();
        require(complete, "wait for six successful frames");
        status = 0;''')
replace('        std::cout << "{\\\"raw\\\":"',
 '        std::cout << "{\\\"raw\\\":"') # retain the audited RAM statistics emitter
assert 'id().find(' not in text and 'meta.status != FrameMetadata::FrameSuccess' in text
source=R/'native-physical-probe.cpp';assert not source.exists();source.write_text(text)
shutil.copyfile(source,sdk/'private/native-physical-probe237.cpp')
cmd=['chroot',str(sdk),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate/usr/include/libcamera','/private/native-physical-probe237.cpp','-L/candidate/usr/lib','-Wl,-rpath-link,/candidate/usr/lib','-lcamera','-lcamera-base','-o','/private/native-physical-probe237']
result=subprocess.run(cmd,capture_output=True,timeout=120)
(P/'probe-build-private.log').write_bytes(result.stdout+result.stderr)
assert result.returncode==0,'inspect private compiler log'
target=P/'native-physical-probe237';shutil.copyfile(sdk/'private/native-physical-probe237',target)
report=dict(stage=237,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),binary_bytes=target.stat().st_size,
 exact_of_id_model_entity=True,frame_success_and_monotonic_timestamps_required=True,finite_six_frames=True,packed_raw_padding_excluded=True,dma_buf_sync_start_end=True,no_scene_pixels_written=True,compiler_werror_clean=True)
(R/'physical-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
