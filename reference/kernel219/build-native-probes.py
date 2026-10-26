from pathlib import Path
import hashlib,json,shutil,subprocess

here=Path(__file__).resolve().parent;root=Path('/home/cy122/x2pro-linux/libcamera214-root')
original=(here.parent/'kernel213/raw-dark-sync-probe.cpp').read_text()
text=original
changes=[
    ('Capture(std::shared_ptr<Camera> camera, bool raw, const StreamConfiguration &cfg)',
     'Capture(std::shared_ptr<Camera> camera, bool raw, const StreamConfiguration &cfg, unsigned int cfaCell)'),
    ('stride_(cfg.stride) {}','stride_(cfg.stride), cfaCell_(cfaCell) {}'),
    ('unsigned int width_, height_, stride_;','unsigned int width_, height_, stride_, cfaCell_;'),
    ('width_ != 1928 || height_ != 1088 || stride_ != 2416 || bytes != stride_ * height_',
     'width_ % 4 || stride_ < width_ / 4 * 5 || bytes != size_t(stride_) * height_'),
    ('if (argc != 4 ||','if (argc != 7 ||'),
    ('const int selected = std::stoi(argv[3]);','const int selected = std::stoi(argv[3]);\n    const unsigned int wantedWidth = std::stoul(argv[4]);\n    const unsigned int wantedHeight = std::stoul(argv[5]);\n    const unsigned int cfaCell = std::stoul(argv[6]);\n    require(wantedWidth >= 4 && wantedWidth <= 4608 && wantedWidth % 4 == 0 && wantedHeight >= 4 && wantedHeight <= 3456 && wantedHeight % 4 == 0 && (cfaCell == 1 || cfaCell == 2), "supported probe dimensions/CFA");'),
    ('streamConfiguration.size = {raw ? 1928U : 1920U, 1088};','streamConfiguration.size = { wantedWidth, wantedHeight };'),
    ('require(camera->configure(configuration.get()) == 0, "configure front camera");','require(streamConfiguration.size == Size(wantedWidth, wantedHeight), "requested native dimensions retained");\n        require(camera->configure(configuration.get()) == 0, "configure front camera");'),
    ('std::make_unique<Capture>(camera, raw, streamConfiguration)','std::make_unique<Capture>(camera, raw, streamConfiguration, cfaCell)'),
]
for old,new in changes:
    assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
# Statistics are indexed by same-colour CFA cells in the full mode.
old='(row % 2) * 2 + column % 2'
if old not in text:
    candidates=[l for l in text.splitlines() if 'row' in l and '& 1' in l]
    raise AssertionError('Inspect CFA statistics indexing: '+repr(candidates))
text=text.replace(old,'((row / cfaCell_) % 2) * 2 + (column / cfaCell_) % 2')
source=here/'native-mode-probe.cpp';assert not source.exists();source.write_text(text)
shutil.copyfile(source,root/'private/native-mode-probe219.cpp')
command=['chroot',str(root),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-pthread','-I/candidate/usr/include/libcamera','/private/native-mode-probe219.cpp','-L/candidate/usr/lib','-Wl,-rpath-link,/candidate/usr/lib','-lcamera','-lcamera-base','-o','/private/native-mode-probe219']
p=subprocess.run(command,capture_output=True,timeout=120)
(Path('/mnt/e/edk2-samurai-out/kernel219')/'probe-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
target=Path('/mnt/e/edk2-samurai-out/kernel219/native-mode-probe219');shutil.copyfile(root/'private/native-mode-probe219',target)
report=dict(stage=219,probe_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),probe_bytes=target.stat().st_size,
            exact_native_dimensions_checked=True,packed_raw_row_padding_excluded=True,dma_sync_read_start_end=True,
            raw_cfa_statistics_cell_size_explicit=True,no_scene_frames_saved=True)
(here/'native-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
