/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Source-function harness only: no devices or libcamera application runtime. */
#include "source-under-test.inc"

#include <cassert>
#include <iostream>

using namespace libcamera;

int main(int argc, char **argv)
{
	assert(argc == 2);
	const bool candidate = std::string(argv[1]) == "candidate";
	assert(candidate || std::string(argv[1]) == "baseline");
	unsigned int checks = 0;
	auto expect = [&](bool result) { assert(result); ++checks; };
	auto space = [&](const std::optional<ColorSpace> &actual,
			 ColorSpace::YcbcrEncoding encoding, ColorSpace::Range range) {
		expect(actual && actual->ycbcrEncoding == encoding && actual->range == range);
	};
	const auto &info = MediaBusFormatInfo::info(MEDIA_BUS_FMT_UYYVYY10_0_5X30);
	expect(info.isValid() == candidate);
	if (candidate) {
		expect(info.code == 0x2027 && std::string(info.name) == "UYYVYY10_0_5X30");
		expect(info.type == MediaBusFormatInfo::Type::Image && info.bitsPerPixel == 15);
		expect(info.colourEncoding == PixelFormatInfo::ColourEncodingYUV);
	}
	for (auto [code, bits, encoding] : {
		std::tuple{MEDIA_BUS_FMT_YUV10_1X30, 30u, PixelFormatInfo::ColourEncodingYUV},
		std::tuple{MEDIA_BUS_FMT_YUV8_1X24, 24u, PixelFormatInfo::ColourEncodingYUV},
		std::tuple{MEDIA_BUS_FMT_RGB888_1X24, 24u, PixelFormatInfo::ColourEncodingRGB},
		std::tuple{MEDIA_BUS_FMT_SRGGB10_1X10, 10u, PixelFormatInfo::ColourEncodingRAW}}) {
		const auto &other = MediaBusFormatInfo::info(code);
		expect(other.isValid() && other.bitsPerPixel == bits && other.colourEncoding == encoding);
	}
	V4L2Subdevice device;
	v4l2_mbus_framefmt format{};
	format.code = MEDIA_BUS_FMT_UYYVYY10_0_5X30;
	warnings = 0;
	expect(!device.toColorSpace(format));
	expect(warnings == 0); /* DEFAULT has no color-space concept and skips lookup. */
	format.colorspace = V4L2_COLORSPACE_SRGB;
	warnings = 0;
	space(device.toColorSpace(format), ColorSpace::YcbcrEncoding::Rec601, ColorSpace::Range::Limited);
	expect(warnings == (candidate ? 0 : 2));
	/* Existing converter defaults can coincide despite an RGB fallback. */
	format.ycbcr_enc = V4L2_YCBCR_ENC_601;
	format.quantization = V4L2_QUANTIZATION_LIM_RANGE;
	space(device.toColorSpace(format), candidate ? ColorSpace::YcbcrEncoding::Rec601 : ColorSpace::YcbcrEncoding::None,
	      candidate ? ColorSpace::Range::Limited : ColorSpace::Range::Full);
	format.quantization = V4L2_QUANTIZATION_FULL_RANGE;
	auto full = device.toColorSpace(format);
	space(full, candidate ? ColorSpace::YcbcrEncoding::Rec601 : ColorSpace::YcbcrEncoding::None, ColorSpace::Range::Full);
	expect(full && full->primaries == ColorSpace::Primaries::Rec709 && full->transferFunction == ColorSpace::TransferFunction::Srgb);
	format.colorspace = V4L2_COLORSPACE_REC709;
	format.ycbcr_enc = V4L2_YCBCR_ENC_709;
	format.quantization = V4L2_QUANTIZATION_LIM_RANGE;
	space(device.toColorSpace(format), candidate ? ColorSpace::YcbcrEncoding::Rec709 : ColorSpace::YcbcrEncoding::None,
	      candidate ? ColorSpace::Range::Limited : ColorSpace::Range::Full);
	format = {};
	format.code = MEDIA_BUS_FMT_UYYVYY10_0_5X30;
	format.colorspace = V4L2_COLORSPACE_JPEG;
	space(device.toColorSpace(format), ColorSpace::YcbcrEncoding::Rec601, ColorSpace::Range::Full);
	/* Unknown values remain unsupported; the new entry is not a global fallback. */
	format.code = 0xffff;
	format.ycbcr_enc = V4L2_YCBCR_ENC_601;
	format.quantization = V4L2_QUANTIZATION_LIM_RANGE;
	warnings = 0;
	space(device.toColorSpace(format), ColorSpace::YcbcrEncoding::None, ColorSpace::Range::Full);
	expect(warnings == 2);
	format.code = MEDIA_BUS_FMT_UYYVYY10_0_5X30;
	format.ycbcr_enc = 0xffff;
	expect(!device.toColorSpace(format));
	format.ycbcr_enc = V4L2_YCBCR_ENC_DEFAULT;
	format.quantization = 0xffff;
	expect(!device.toColorSpace(format));
	format.quantization = V4L2_QUANTIZATION_DEFAULT;
	format.xfer_func = 0xffff;
	expect(!device.toColorSpace(format));
	format.xfer_func = V4L2_XFER_FUNC_DEFAULT;
	format.colorspace = 0xffff;
	expect(!device.toColorSpace(format));
	format = {};
	format.code = MEDIA_BUS_FMT_SRGGB10_1X10;
	format.colorspace = V4L2_COLORSPACE_RAW;
	space(device.toColorSpace(format), ColorSpace::YcbcrEncoding::None, ColorSpace::Range::Full);
	std::cout << "mode=" << argv[1] << " assertions=" << checks << " passed=1\n";
}
