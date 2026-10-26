"""Build a public-API RAW/RGB probe using exactly the proposed focus helper."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');name='focus-raw277'
s=(R.parent/'kernel273/main-control-probe.cpp').read_text()
s=s.replace('#include <libcamera/libcamera.h>','#include <libcamera/libcamera.h>\n#include "focus_stats.h"')
old='static const std::array<std::pair<int, float>, 8> controlPlan = {{{2000,1}, {8000,1}, {32000,1}, {32000,1.5}, {32000,2}, {32000,4}, {32000,8}, {32000,1}}};'
assert s.count(old)==1;s=s.replace(old,'static const std::array<std::pair<int, float>, 8> controlPlan = {{{32000,1}, {32000,1}, {32000,1}, {32000,1}, {32000,1}, {32000,1}, {32000,1}, {32000,1}}};')
s=s.replace('requestedFrames = automaticMode ? 180 : 96;','requestedFrames = automaticMode ? 180 : 24;')
start=s.index('        Measurement rawStats, rgbStats;');end=s.index('        bool again;',start)
s=s[:start]+r'''        auto begin = std::chrono::steady_clock::now();
        auto focus = measureBayerFocus(rawMap.pixels, rawMap.bytes, raw_.size.width, raw_.size.height,
                                      raw_.stride, (raw_.size.width-rgb_.size.width)/2,
                                      (raw_.size.height-rgb_.size.height)/2, rgb_.size.width,
                                      rgb_.size.height, {10,true,true,false});
        auto fom = focus.figureOfMerit();
        require(focus.valid && fom.has_value(), "valid RAW focus statistics");
        auto microseconds = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-begin).count();
        rawMap.finish(); rgbMap.finish();
        std::ostringstream out;
        out << "{\"queued_index\":" << index << ",\"sequence\":" << cm.sequence << ",\"timestamp_ns\":" << cm.timestamp
            << ",\"raw_sequence\":" << rm.sequence << ",\"raw_timestamp_ns\":" << rm.timestamp
            << ",\"exposure_us\":" << *exposure << ",\"analogue_gain\":" << *gain
            << ",\"focus_fom\":" << *fom << ",\"measurement_us\":" << microseconds << ",\"regions\":[";
        bool first = true;
        for (const auto &region : focus.regions) {
            if (!first) out << ',';
            first = false;
            out << "{\"energy\":" << region.energy << ",\"sum\":" << region.sum << ",\"samples\":" << region.samples << '}';
        }
        out << "]}";
'''+s[end:]
(R/(name+'.cpp')).write_text(s)
for file,data in [(name+'.cpp',s.encode()),('focus_stats.h',(R/'focus_stats.h').read_bytes())]:
 p=SDK/'private'/('focus277-'+file);assert not p.exists();p.write_bytes(data)
# Put the same header alongside the probe, without modifying any retained source.
source=SDK/'private'/('focus277-'+name+'.cpp')
s=source.read_text().replace('#include "focus_stats.h"','#include "focus277-focus_stats.h"');source.write_text(s)
prefix='/candidate275-r22'
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+prefix+'/usr/include/libcamera','/private/'+source.name,'-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib','-lcamera','-lcamera-base','-o','/private/'+name],capture_output=True,timeout=90)
(host.PRIVATE/'focus-probe-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
target=host.PRIVATE/name;shutil.copyfile(SDK/'private'/name,target)
d=dict(stage=277,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((R/(name+'.cpp')).read_bytes()).hexdigest(),
 focus_helper_sha256=hashlib.sha256((R/'focus_stats.h').read_bytes()).hexdigest(),cpp20_werror_clean=True,public_libcamera_api=True,
 fixed_exposure_us=32000,fixed_analogue_gain=1,frames_per_capture=24,no_pixels_written=True)
(R/'focus-probe-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
