"""Edit only the isolated 218 source. This is an experimental candidate."""
from pathlib import Path
import difflib, hashlib, json, shutil

here = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel218')
root = Path('/home/cy122/x2pro-linux/libcamera214-root')
src = root/'work/libcamera218'
original = root/'work/libcamera/src/libcamera-v0.7.2'
changes = []

def edit(name, replacements):
    path = src/name
    before = path.read_text()
    assert before == (original/name).read_text(), name+' already edited'
    after = before
    for old, new in replacements:
        assert after.count(old) == 1, (name, old[:120], after.count(old))
        after = after.replace(old, new)
    path.write_text(after)
    changes.append((name, before, after))

edit('src/libcamera/software_isp/debayer_cpu.h', [
    ('#include "debayer.h"', '#include "debayer.h"\n#include "native_quad_bayer.h"'),
    ('DebayerCpu(std::unique_ptr<SwStatsCpu> stats, const CameraManager &cm);',
     'DebayerCpu(std::unique_ptr<SwStatsCpu> stats, const CameraManager &cm, bool imx471 = false);'),
    ('\tdebayerFn debayer0_;', '''
	bool imx471_;
	bool nativeQuadEnabled_ = false;
	bool nativeQuad_ = false;
	bool nativeQuadAlpha_ = false;
	bool nativeQuadBgr_ = false;
	NativeQuadBayer nativeQuadDecoder_;
	Size inputSize_;

	debayerFn debayer0_;''')])

edit('include/libcamera/internal/software_isp/swstats_cpu.h', [
    ('\tint configure(const StreamConfiguration &inputCfg, unsigned int statsBufferCount = 1);',
     '\tvoid setQuadBayer(bool enabled) { quadBayer_ = enabled; }\n\tint configure(const StreamConfiguration &inputCfg, unsigned int statsBufferCount = 1);')])

edit('src/libcamera/software_isp/debayer_cpu.cpp', [
    ('\tvoid process4(uint32_t frame, const uint8_t *src, uint8_t *dst);',
     '\tvoid process4(uint32_t frame, const uint8_t *src, uint8_t *dst);\n\tvoid processNativeQuad(const uint8_t *src, uint8_t *dst);'),
    ('\tbool enableInputMemcpy_;', '\tbool enableInputMemcpy_;\n\tNativeQuadBayer::Workspace nativeQuadWorkspace_;'),
    ('DebayerCpu::DebayerCpu(std::unique_ptr<SwStatsCpu> stats, const CameraManager &cm)\n\t: Debayer(cm), stats_(std::move(stats))',
     'DebayerCpu::DebayerCpu(std::unique_ptr<SwStatsCpu> stats, const CameraManager &cm, bool imx471)\n\t: Debayer(cm), stats_(std::move(stats)), imx471_(imx471)'),
    ('\tunsigned int threadCount =', '''	/* Private board experiment: the fourcc does not describe a 4x4 CFA. */
	nativeQuadEnabled_ = configuration.option<bool>(
		{ "software_isp", "experimental_imx471_native_quad" }).value_or(false);

	unsigned int threadCount ='''),
    ('\tif (getInputConfig(inputCfg.pixelFormat, inputConfig_) != 0) {', '''	nativeQuad_ = imx471_ && inputCfg.size == Size(4608, 3456);
	if (nativeQuad_ && !nativeQuadEnabled_)
		return -EINVAL;
	inputSize_ = inputCfg.size;
	if (getInputConfig(inputCfg.pixelFormat, inputConfig_) != 0) {'''),
    ('\tif (stats_->configure(inputCfg, threads_.size()) != 0)', '''	stats_->setQuadBayer(nativeQuad_);
	if (nativeQuad_)
		inputConfig_.patternSize = { 4, 4 };
	if (stats_->configure(inputCfg, threads_.size()) != 0)'''),
    ('''int ret = setDebayerFunctions(inputCfg.pixelFormat,
				      outputCfg.pixelFormat,
				      ccmEnabled);
	if (ret != 0)
		return -EINVAL;''', '''if (nativeQuad_) {
		const BayerFormat bayer = BayerFormat::fromPixelFormat(inputCfg.pixelFormat);
		const Point shift = quadBayerOrderShifts(bayer.order);
		if (!isQuadBayerInputFormatSupported(inputCfg.pixelFormat) ||
		    !nativeQuadDecoder_.configure(inputCfg.size.width, inputCfg.size.height,
					 inputCfg.stride, shift.x / 2, shift.y / 2) ||
		    getOutputConfig(outputCfg.pixelFormat, outputConfig_) != 0)
			return -EINVAL;
		std::tie(outputConfig_.stride, outputConfig_.frameSize) =
			strideAndFrameSize(outputCfg.pixelFormat, outputCfg.size);
		nativeQuadAlpha_ = outputConfig_.bpp == 32;
		nativeQuadBgr_ = outputCfg.pixelFormat == formats::RGB888 ||
				 outputCfg.pixelFormat == formats::XRGB8888 ||
				 outputCfg.pixelFormat == formats::ARGB8888;
		swapRedBlueGains_ = false;
	} else {
		int ret = setDebayerFunctions(inputCfg.pixelFormat,
					      outputCfg.pixelFormat, ccmEnabled);
		if (ret != 0)
			return -EINVAL;
	}'''),
    ('\t/* Adjust src to top left corner of the window */', '''	if (debayer_->nativeQuad_) {
		processNativeQuad(src, dst);
	} else {
	/* Adjust src to top left corner of the window */'''),
    ('\tdebayer_->workPendingMutex_.lock();', '\t}\n\n\tdebayer_->workPendingMutex_.lock();'),
    ('void DebayerCpuThread::process2(uint32_t frame, const uint8_t *src, uint8_t *dst)', '''void DebayerCpuThread::processNativeQuad(const uint8_t *src, uint8_t *dst)
{
	auto *d = debayer_;
	d->nativeQuadDecoder_.processRows(src, size_t(d->inputConfig_.stride) * d->inputSize_.height,
		yStart_, yEnd_, nativeQuadWorkspace_, [&](unsigned int x, unsigned int y, auto rgb) {
			uint8_t r, g, b;
			if (d->ccmEnabled_) {
				const auto &red = d->redCcm_[rgb[0] >> 2];
				const auto &green = d->greenCcm_[rgb[1] >> 2];
				const auto &blue = d->blueCcm_[rgb[2] >> 2];
				auto gamma = [&](int value) { return d->gammaLut_[std::clamp(value, 0, 255)]; };
				r = gamma(red.r + green.r + blue.r);
				g = gamma(red.g + green.g + blue.g);
				b = gamma(red.b + green.b + blue.b);
			} else {
				r = d->red_[rgb[0] >> 2];
				g = d->green_[rgb[1] >> 2];
				b = d->blue_[rgb[2] >> 2];
			}
			uint8_t *pixel = dst + size_t(y) * d->outputConfig_.stride +
					size_t(x) * (d->nativeQuadAlpha_ ? 4 : 3);
			pixel[0] = d->nativeQuadBgr_ ? b : r;
			pixel[1] = g;
			pixel[2] = d->nativeQuadBgr_ ? r : b;
			if (d->nativeQuadAlpha_)
				pixel[3] = 255;
		});
}

void DebayerCpuThread::process2(uint32_t frame, const uint8_t *src, uint8_t *dst)'''),
    ('\tstats_->startFrame(frame);', '''	if (nativeQuad_ &&
	    (in.planes()[0].size() < size_t(inputConfig_.stride) * inputSize_.height ||
	     out.planes()[0].size() < outputConfig_.frameSize)) {
		metadata.status = FrameMetadata::FrameError;
		dmaSyncers.clear();
		outputBufferReady.emit(output);
		inputBufferReady.emit(input);
		return;
	}
	if (!nativeQuad_)
		stats_->startFrame(frame);'''),
    ('\tmetadata.planes()[0].bytesused = out.planes()[0].size();', '''	if (nativeQuad_)
		stats_->processFrame(frame, 0, in);

	metadata.planes()[0].bytesused = out.planes()[0].size();'''),
    ('\tstats_->finishFrame(frame, 0);', '\tif (!nativeQuad_)\n\t\tstats_->finishFrame(frame, 0);'),
    ('\tSize patternSize = this->patternSize(inputFormat);', '''	if (imx471_ && inputSize == Size(4608, 3456)) {
		if (!nativeQuadEnabled_ || !isQuadBayerInputFormatSupported(inputFormat))
			return {};
		return SizeRange(inputSize);
	}
	Size patternSize = this->patternSize(inputFormat);'''),
    ('#include "libcamera/internal/mapped_framebuffer.h"',
     '#include "libcamera/internal/mapped_framebuffer.h"\n#include "libcamera/internal/software_isp/quad_bayer.h"')])

edit('include/libcamera/internal/software_isp/software_isp.h', [
    ('\tbool ccmEnabled_;', '\tbool ccmEnabled_;\n\tbool imx471_ = false;\n\tbool nativeQuadCpu_ = false;')])
edit('src/libcamera/software_isp/software_isp.cpp', [
    ('\tconst bool quadBayer = softwareIspNeedsCellCollapse(sensor->model());', '''	const bool quadBayer = softwareIspNeedsCellCollapse(sensor->model());
	imx471_ = sensor->model() == "imx471";
	const GlobalConfiguration &nativeConfiguration = cm._d()->configuration();
	const bool nativeQuadExperiment = imx471_ && nativeConfiguration.option<bool>(
		{ "software_isp", "experimental_imx471_native_quad" }).value_or(false);'''),
    ('\tif (!softISPMode || softISPMode == "gpu") {', '''	if (nativeQuadExperiment && softISPMode == "gpu") {
		LOG(SoftwareIsp, Error) << "Native Quad Bayer experiment requires CPU mode";
		return;
	}
	if ((!softISPMode || softISPMode == "gpu") && !nativeQuadExperiment) {'''),
    ('\tif (!debayer_)\n\t\tdebayer_ = std::make_unique<DebayerCpu>(std::move(stats), cm);', '''	if (!debayer_) {
		debayer_ = std::make_unique<DebayerCpu>(std::move(stats), cm, imx471_);
		nativeQuadCpu_ = true;
	}'''),
    ('\treturn debayer_->sizes(inputFormat, inputSize);', '''	if (imx471_ && inputSize == Size(4608, 3456) && !nativeQuadCpu_)
		return {};
	return debayer_->sizes(inputFormat, inputSize);'''),
    ('\tint ret = ipa_->configure(configInfo);', '''	if (imx471_ && inputCfg.size == Size(4608, 3456) && !nativeQuadCpu_)
		return -EINVAL;
	int ret = ipa_->configure(configInfo);''')])

name='src/libcamera/software_isp/native_quad_bayer.h'
content=(here/'native_quad_bayer.h').read_text()
assert not (src/name).exists()
(src/name).write_text(content)
changes.append((name,'',content))
edit('test/meson.build', [
    ("    {'name': 'quad-bayer', 'sources': ['quad-bayer.cpp']},", "    {'name': 'quad-bayer', 'sources': ['quad-bayer.cpp']},\n    {'name': 'native-quad', 'sources': ['native-quad.cpp'], 'dependencies': [libthreads]},")])
test=(here/'native-quad-test.cpp').read_text().replace('#include "native_quad_bayer.h"','#include "../src/libcamera/software_isp/native_quad_bayer.h"')
(src/'test/native-quad.cpp').write_text(test)
changes.append(('test/native-quad.cpp','',test))
patch=''.join(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name)) for name,before,after in changes)
(here/'libcamera-native-quad-candidate.patch').write_text(patch)
report=dict(stage=218,isolated_source_only=True,experimental_option_default_false=True,
            mode_aware_imx471_full_only=True,no_cell_collapse_in_output=True,
            full_output_size=[4608,3456],quad_stats_separate_from_pixel_output=True,
            ordinary_modes_use_existing_cpu_path=True,gpu_full_mode_rejected=True,
            no_package_or_device_replacement=True,
            files={name:hashlib.sha256(after.encode()).hexdigest() for name,_,after in changes})
(here/'candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
