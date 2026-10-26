"""Add numeric 4x4 phase statistics inside each colour-bar plateau."""
from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel219');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
text=(here/'native-mode-probe.cpp').read_text()
changes=[
 ('    std::array<double, 8> horizontalMean;','    std::array<double, 8> horizontalMean;\n    std::array<double, 128> segmentPhaseMean;'),
 ('        std::array<uint64_t, 8> segmentSum{}, segmentCount{};','        std::array<uint64_t, 8> segmentSum{}, segmentCount{};\n        std::array<uint64_t, 128> phaseSum{}, phaseCount{};'),
 ('                ++segmentCount[segment];','''                ++segmentCount[segment];
                const unsigned int barWidth = width_ / 8;
                const unsigned int barPosition = column % barWidth;
                if (barPosition >= barWidth / 4 && barPosition < 3 * barWidth / 4 && row >= 16 && row + 16 < height_) {
                    const unsigned int phase = segment * 16 + (row % 4) * 4 + column % 4;
                    phaseSum[phase] += value;
                    ++phaseCount[phase];
                }'''),
 ('                         {}, {}};', '                         {}, {}, {}};'),
 ('        previous_ = std::move(active);','''        for (unsigned int index = 0; index < 128; ++index)
            stats.segmentPhaseMean[index] = phaseCount[index] ? double(phaseSum[index]) / phaseCount[index] : -1.0;
        previous_ = std::move(active);'''),
]
for old,new in changes:assert text.count(old)==1,old;text=text.replace(old,new)
marker='            std::cout << "]}";'
assert text.count(marker)==1
text=text.replace(marker,'''            std::cout << "],\\"test_pattern_segment_phase4x4\\":[";
            for (unsigned int index = 0; index < 128; ++index) {
                if (index) std::cout << ',';
                std::cout << frame.segmentPhaseMean[index];
            }
            std::cout << "]}";''')
source=here/'pattern-layout-probe.cpp';assert not source.exists();source.write_text(text);shutil.copyfile(source,root/'private/pattern-layout-probe219.cpp')
command=['chroot',str(root),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate/usr/include/libcamera','/private/pattern-layout-probe219.cpp','-L/candidate/usr/lib','-Wl,-rpath-link,/candidate/usr/lib','-lcamera','-lcamera-base','-o','/private/pattern-layout-probe219']
p=subprocess.run(command,capture_output=True,timeout=120);(private/'pattern-layout-compile-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
target=private/'pattern-layout-probe219';assert not target.exists();shutil.copyfile(root/'private/pattern-layout-probe219',target)
r=dict(stage=219,test_pattern_layout_probe_built=True,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,
 raw10_full_active_pixels_dma_synced=True,colour_bar_central_half_excludes_boundary_mixing=True,
 period2_and_period4_evaluation_pending=True,real_scene_colour_filter_layout_not_claimed=True)
(here/'pattern-layout-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
