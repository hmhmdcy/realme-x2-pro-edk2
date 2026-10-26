from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel238');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((R/'controlled-rear-r2-validation.json').read_text())['passed']
text=(R/'physical-control-probe.cpp').read_text().replace('double(histogram[1023])','double(histogram[raw_ ? 1023 : 255])')
old='            active.assign(pixels, pixels + bytes);';assert text.count(old)==1
text=text.replace(old,'''            require(stride_ >= width_ * 3 && bytes == size_t(stride_) * height_, "RGB geometry and bytesused");
            active.reserve(size_t(width_) * height_ * 3);
            for (unsigned int row = 0; row < height_; ++row) {
                const uint8_t *line = pixels + size_t(row) * stride_;
                active.insert(active.end(), line, line + width_ * 3);
            }''')
source=R/'physical-rgb-control-probe.cpp';assert not source.exists();source.write_text(text);shutil.copyfile(source,SDK/'private/physical-rgb-control-probe238.cpp')
cmd=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate238-r14/usr/include/libcamera','/private/physical-rgb-control-probe238.cpp','-L/candidate238-r14/usr/lib','-Wl,-rpath-link,/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-o','/private/physical-rgb-control-probe238']
p=subprocess.run(cmd,capture_output=True,timeout=180);(P/'rgb-control-probe-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
target=P/'physical-rgb-control-probe238';shutil.copyfile(SDK/'private/physical-rgb-control-probe238',target)
report=dict(stage=238,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),binary_bytes=target.stat().st_size,rgb_active_row_padding_excluded=True,rgb_saturation255_used=True,exact_physical_selector_and_all_capture_metadata_checks_preserved=True,werror_clean=True)
(R/'rgb-control-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
