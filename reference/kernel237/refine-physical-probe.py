"""Complete explicit probe cleanup and rebuild the not-yet-deployed binary."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel237');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
path=R/'native-physical-probe.cpp';text=path.read_text()
def replace(old,new):
 global text
 assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
replace('    ~PatternGuard()\n    {\n        if (fd_ < 0)\n            return;',
 '''    bool restore()
    {
        if (fd_ < 0) return true;''')
replace('        if (ioctl(fd_, VIDIOC_S_CTRL, &control) != 0)\n            std::cerr << "ERROR: sensor pattern restore failed\\n";\n        close(fd_);\n    }',
 '''        bool ok = ioctl(fd_, VIDIOC_S_CTRL, &control) == 0;
        control.value = -1;
        ok = ioctl(fd_, VIDIOC_G_CTRL, &control) == 0 && control.value == original_ && ok;
        if (ok) { close(fd_); fd_ = -1; }
        return ok;
    }
    ~PatternGuard() { if (!restore()) std::cerr << "ERROR: sensor pattern restore failed\\n"; if (fd_ >= 0) close(fd_); }''')
replace('    int64_t sensorTimestamp;','    int64_t sensorTimestamp;\n    uint64_t bytesUsed;')
replace('stride_(cfg.stride), cfaCell_(cfaCell) {}','stride_(cfg.stride), cfaCell_(cfaCell), stream_(cfg.stream()) {}')
replace('    void completed(Request *request)\n    {',
 '''    void completed(Request *request)
    {
        try { completedChecked(request); }
        catch (...) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true; ready_.notify_all();
        }
    }
    void completedChecked(Request *request)
    {
        { std::lock_guard<std::mutex> lock(mutex_); if (frames_.size() >= 6 || failed_) return; }''')
replace('request->buffers().size() != 1)', 'request->buffers().size() != 1 || request->buffers().begin()->first != stream_)')
replace('request->metadata().get(controls::SensorTimestamp).value_or(-1), low, high, mean,','request->metadata().get(controls::SensorTimestamp).value_or(-1), bytes, low, high, mean,')
replace('                      << ",\\\"byte_min\\\":" << frame.minimum','                      << ",\\\"bytesused\\\":" << frame.bytesUsed\n                      << ",\\\"byte_min\\\":" << frame.minimum')
replace('    std::vector<uint16_t> previous_;','    Stream *stream_;\n    std::vector<uint16_t> previous_;')
replace('        require(bool(configuration), "generate physical camera configuration");','        require(bool(configuration) && configuration->size() == 1, "generate single physical stream");')
replace('        pattern.reset();\n        capture->print();\n        require(complete, "wait for six successful frames");','        require(pattern->restore(), "restore sensor pattern with readback");\n        pattern.reset();\n        require(complete, "wait for six successful frames");')
replace('    if (started)\n        camera->stop();','    if (started && camera->stop() != 0) status = 1;')
replace('    pattern.reset();\n    requests.clear();','    if (pattern && !pattern->restore()) { std::cerr << "ERROR: pattern recovery\\n"; status = 1; }\n    pattern.reset();\n    requests.clear();')
replace('    if (acquired)\n        camera->release();\n    capture.reset();','    if (acquired && camera->release() != 0) { std::cerr << "ERROR: release camera\\n"; status = 1; }\n    if (capture) capture->print();\n    capture.reset();')
path.write_text(text)
shutil.copyfile(path,sdk/'private/native-physical-probe237.cpp')
cmd=['chroot',str(sdk),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate/usr/include/libcamera','/private/native-physical-probe237.cpp','-L/candidate/usr/lib','-Wl,-rpath-link,/candidate/usr/lib','-lcamera','-lcamera-base','-o','/private/native-physical-probe237']
result=subprocess.run(cmd,capture_output=True,timeout=120);(P/'probe-build-r2-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,'inspect private compiler log'
target=P/'native-physical-probe237';shutil.copyfile(sdk/'private/native-physical-probe237',target)
report=dict(stage=237,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),binary_bytes=target.stat().st_size,exact_of_id_model_entity=True,frame_success_and_monotonic_timestamps_required=True,finite_six_frames=True,one_expected_stream_plane=True,bytesused_recorded=True,callback_exceptions_caught=True,explicit_pattern_stop_release_checked=True,packed_raw_padding_excluded=True,dma_buf_sync_start_end=True,no_scene_pixels_written=True,compiler_werror_clean=True,timestamps_are_buffer_completion_not_exposure_start=True)
(R/'physical-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
