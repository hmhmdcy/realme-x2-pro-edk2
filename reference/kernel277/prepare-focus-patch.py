"""Add RAW spatial focus statistics to the generic software ISP, without AF policy."""
from pathlib import Path
import difflib,hashlib,json
R=Path(__file__).resolve().parent
S=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera275-r22-built/src/libcamera-v0.7.2')
names=['include/libcamera/internal/software_isp/meson.build','include/libcamera/internal/software_isp/swisp_stats.h',
 'include/libcamera/internal/software_isp/swstats_cpu.h','src/libcamera/software_isp/swstats_cpu.cpp',
 'src/libcamera/software_isp/debayer_cpu.cpp','src/ipa/simple/soft_simple.cpp']
before={n:(S/n).read_text() for n in names};after=dict(before)
def change(name,old,new):
 assert after[name].count(old)==1,(name,old);after[name]=after[name].replace(old,new)
change(names[0],"    'debayer_params.h',","    'debayer_params.h',\n    'focus_stats.h',")
change(names[1],'#include "libcamera/internal/vector.h"','#include "libcamera/internal/vector.h"\n#include "libcamera/internal/software_isp/focus_stats.h"')
change(names[1],'\tbool valid;','\tbool valid;\n\t/** \\brief Frame identity of this shared statistics snapshot. */\n\tuint32_t frame;\n\t/** \\brief RAW spatial contrast, before colour/gamma/sharpening. */\n\tFocusStatistics focus;')
change(names[2],'\tvoid startFrame(uint32_t frame);','\tvoid startFrame(uint32_t frame);\n\tvoid processFocusStats(uint32_t frame, MappedFrameBuffer &input, const Rectangle &window);')
change(names[2],'\tunsigned int stride_;','\tunsigned int stride_;\n\tSize inputSize_;\n\tBayerFormat focusFormat_;')
change(names[3],'\tsharedStats_->valid = valid;','\tsharedStats_->frame = frame;\n\tsharedStats_->valid = valid;')
change(names[3],'''\tstride_ = inputCfg.stride;
\tstats_.resize(statsBufferCount);''','''\tstride_ = inputCfg.stride;
\tinputSize_ = inputCfg.size;
\tfocusFormat_ = BayerFormat::fromPixelFormat(inputCfg.pixelFormat);
\tstats_.resize(statsBufferCount);''')
anchor='/**\n * \\brief Calculate statistics for a frame in one go'
addition='''/**
 * \\brief Gather spatial green contrast before returning the input buffer
 * \\param[in] frame Frame identity, with the same cadence as colour statistics
 * \\param[in] input Mapped and DMA-synchronized RAW input
 * \\param[in] window Input-relative crop corresponding to the processed image
 */
void SwStatsCpu::processFocusStats(uint32_t frame, MappedFrameBuffer &input,
\t\t\t\t const Rectangle &window)
{
\tif (frame % kStatPerNumFrames)
\t\treturn;

\tsharedStats_->focus = {};
\tif (input.planes().empty() || window.x < 0 || window.y < 0)
\t\treturn;
\tif (focusFormat_.packing != BayerFormat::Packing::None &&
\t    focusFormat_.packing != BayerFormat::Packing::CSI2)
\t\treturn;

\tFocusBayerFormat format{
\t\tfocusFormat_.bitDepth,
\t\tfocusFormat_.packing == BayerFormat::Packing::CSI2,
\t\tfocusFormat_.order == BayerFormat::GBRG ||
\t\t\tfocusFormat_.order == BayerFormat::GRBG,
\t\tquadBayer_,
\t};
\tsharedStats_->focus = measureBayerFocus(input.planes()[0].data(),
\t\t\t\t\t      input.planes()[0].size(),
\t\t\t\t\t      inputSize_.width, inputSize_.height, stride_,
\t\t\t\t\t      window.x, window.y, window.width, window.height,
\t\t\t\t\t      format);
}

'''
change(names[3],anchor,addition+anchor)
change(names[3],'''\t(this->*processFrame_)(input);
\tfinishFrame(frame, bufferId);''','''\t(this->*processFrame_)(input);
\tprocessFocusStats(frame, input, window_);
\tfinishFrame(frame, bufferId);''')
change(names[4],'''\tif (nativeQuad_)
\t\tstats_->processFrame(frame, 0, in);

\tmetadata.planes()''','''\tif (nativeQuad_)
\t\tstats_->processFrame(frame, 0, in);
\telse
\t\tstats_->processFocusStats(frame, in, window_);

\tmetadata.planes()''')
change(names[5],'\tControlInfoMap::Map map = context_.ctrlMap;','\tcontext_.ctrlMap[&controls::FocusFoM] = ControlInfo(0, INT32_MAX);\n\tControlInfoMap::Map map = context_.ctrlMap;')
change(names[5],'''\tControlList metadata(controls::controls);
\tfor (const auto &algo : algorithms())''','''\tControlList metadata(controls::controls);
\t/* Never report a cached focus score as belonging to another frame. */
\tif (stats_->valid && stats_->frame == frame) {
\t\tif (auto focus = stats_->focus.figureOfMerit())
\t\t\tmetadata.set(controls::FocusFoM, *focus);
\t}
\tfor (const auto &algo : algorithms())''')
new='include/libcamera/internal/software_isp/focus_stats.h';after[new]=(R/'focus_stats.h').read_text()
patch=''.join(''.join(difflib.unified_diff(before.get(n,'').splitlines(True),after[n].splitlines(True),
 fromfile='a/'+n if n in before else '/dev/null',tofile='b/'+n)) for n in after)
header='''Subject: [PATCH] software_isp: gather spatial RAW focus statistics

Add bounded green-channel contrast statistics before software colour processing.
Return the combined measurement through standard FocusFoM metadata, only when
the statistics snapshot belongs to this frame. Sample all supported packed and
unpacked Bayer formats, using the correct native quad green phase where needed.

This supplies measurement infrastructure for contrast AF. It implements neither
AF search nor a DAC-to-dioptre calibration, and contains no board/lens policy.
---
'''
(R/'0027-softisp-raw-focus-statistics.patch').write_text(header+patch)
proof=dict(stage=277,patch_count=27,source_before_files={n:hashlib.sha256(s.encode()).hexdigest() for n,s in before.items()},
 source_files={n:hashlib.sha256(s.encode()).hexdigest() for n,s in after.items()},
 new_source_files=[new],standard_focus_fom_metadata=True,raw_green_grid=True,frame_identity_checked=True,
 no_board_lens_application_conditionals=True,af_algorithm_not_implemented=True,not_built_or_deployed=True)
(R/'focus-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(stage=277,files=len(after),patch_count=27)))
