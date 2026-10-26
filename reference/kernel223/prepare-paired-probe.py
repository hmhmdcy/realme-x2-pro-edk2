from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel223');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
text=(here.parent/'kernel222/request-gap-probe.cpp').read_text()
changes=[
 ('unsigned int request, buffer;','unsigned int request, buffer;\n    uint64_t timestamp;'),
 ('class Capture {\npublic:\n','class Capture {\npublic:\n    explicit Capture(bool raw) : raw_(raw) {}\n'),
 ('buffer.status != FrameMetadata::FrameSuccess || !exposure || !gain','buffer.status != FrameMetadata::FrameSuccess || (!raw_ && (!exposure || !gain))'),
 ('records.push_back({ request->sequence(), buffer.sequence, *exposure, *gain });','records.push_back({ request->sequence(), buffer.sequence, buffer.timestamp, exposure.value_or(-1), gain.value_or(-1.0f) });'),
 ('    std::mutex mutex;','    bool raw_;\n    std::mutex mutex;'),
 ('int main()\n{','int main(int argc, char **argv)\n{\n    if (argc != 4) return 2;\n    const bool raw = std::string(argv[1]) == "raw";\n    const unsigned int width = std::stoul(argv[2]), height = std::stoul(argv[3]);\n    if (!((raw && width == 1928 && height == 1088) || (raw && width == 2304 && height == 1728) || (!raw && width == 1920 && height == 1088) || (!raw && width == 2296 && height == 1728))) return 2;'),
 ('    Capture capture;','    Capture capture(raw);'),
 ('{ StreamRole::Viewfinder }','{ raw ? StreamRole::Raw : StreamRole::Viewfinder }'),
 ('cfg.size = { 1920, 1088 }; cfg.pixelFormat = formats::RGB888;','cfg.size = { width, height }; cfg.pixelFormat = raw ? formats::SRGGB10_CSI2P : formats::RGB888;'),
 ('cfg.size == Size(1920, 1088)','cfg.size == Size(width, height) && cfg.pixelFormat == (raw ? formats::SRGGB10_CSI2P : formats::RGB888)'),
 ('std::cout << "{\\\"width\\\":1920,\\\"height\\\":1088,\\\"stride\\\":" << cfg.stride', 'std::cout << "{\\\"width\\\":" << width << ",\\\"height\\\":" << height << ",\\\"stride\\\":" << cfg.stride'),
 ('<< ",\\\"buffer_sequence\\\":" << r.buffer << ",\\\"exposure_us\\\":" << r.exposure','<< ",\\\"buffer_sequence\\\":" << r.buffer << ",\\\"timestamp_ns\\\":" << r.timestamp << ",\\\"exposure_us\\\":" << r.exposure'),
]
for old,new in changes:assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
(here/'paired-frame-probe.cpp').write_text(text);source=root/'private/paired-frame-probe223.cpp';assert not source.exists();shutil.copyfile(here/'paired-frame-probe.cpp',source)
args=['chroot',str(root),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate220/usr/include/libcamera','/private/paired-frame-probe223.cpp','-L/candidate220/usr/lib','-Wl,-rpath-link,/candidate220/usr/lib','-lcamera','-lcamera-base','-o','/private/paired-frame-probe223']
p=subprocess.run(args,capture_output=True,timeout=150);(private/'paired-probe-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
target=private/'paired-frame-probe';shutil.copyfile(root/'private/paired-frame-probe223',target)
r=dict(stage=223,source_sha256=hashlib.sha256(text.encode()).hexdigest(),binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,client_pixels_not_mapped=True,eof_buffer_timestamps_recorded=True,raw_and_rgb_metadata_modes=True,request_gaps_milliseconds=500,requests_per_stream=16)
(here/'paired-probe-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
