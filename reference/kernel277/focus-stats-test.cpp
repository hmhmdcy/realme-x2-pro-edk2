/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "focus_stats.h"
#include <cassert>
#include <iostream>

using namespace libcamera;

static std::vector<uint8_t> encode(unsigned int width, unsigned int height,
				 unsigned int stride, const FocusBayerFormat &format,
				 double contrast = 1, bool colourOnly = false,
				 int constant = -1)
{
	std::vector<uint8_t> bytes(size_t(stride) * height, 0x5a);
	for (unsigned int y = 0; y < height; ++y) {
		uint8_t *line = bytes.data() + size_t(y) * stride;
		for (unsigned int x = 0; x < width; ++x) {
			unsigned int cx = format.quad ? x / 2 : x;
			unsigned int cy = format.quad ? y / 2 : y;
			bool green = bool((cx ^ cy) & 1) != format.greenFirst;
			double texture = 180 * std::sin(x * 6.283185307179586 / 64) +
					 140 * std::cos(y * 6.283185307179586 / 96);
			unsigned int value = constant < 0 ? unsigned(std::round(512 +
				(colourOnly && green ? 0 : contrast * texture))) : constant;
			value = format.bits >= 10 ? value << (format.bits - 10) : value >> 2;
			if (!format.packed) {
				if (format.bits == 8) line[x] = value;
				else { line[2*x] = value & 255; line[2*x+1] = value >> 8; }
			} else if (format.bits == 10) {
				size_t base = x / 4 * 5; unsigned int shift = 2 * (x % 4);
				line[base + x % 4] = value >> 2;
				line[base + 4] = (line[base + 4] & ~(3U << shift)) | ((value & 3) << shift);
			} else {
				size_t base = x / 2 * 3; unsigned int shift = 4 * (x % 2);
				line[base + x % 2] = value >> 4;
				line[base + 2] = (line[base + 2] & ~(15U << shift)) | ((value & 15) << shift);
			}
		}
	}
	return bytes;
}

int main()
{
	unsigned int cases = 0;
	for (bool packed : {false, true}) {
		for (unsigned int bits : {8U, 10U, 12U}) {
			if (packed && bits == 8) continue;
			for (bool first : {false, true}) {
				for (bool quad : {false, true}) {
					FocusBayerFormat format{bits, packed, first, quad};
					unsigned int width = 640, height = 480;
					unsigned int stride = (packed ? width * bits / 8 : width * (bits == 8 ? 1 : 2)) + 32;
					auto sharp = encode(width,height,stride,format);
					auto blurred = encode(width,height,stride,format,.25);
					auto measure = [&](const std::vector<uint8_t> &data) {
						return measureBayerFocus(data.data(),data.size(),width,height,stride,0,0,width,height,format);
					};
					auto a = measure(sharp).figureOfMerit(), b = measure(blurred).figureOfMerit();
					assert(a && b && *a > *b * 8 && *b > 0);
					assert(measure(encode(width,height,stride,format,1,true)).figureOfMerit().value() == 0);
					assert(measure(encode(width,height,stride,format,1,false,512)).figureOfMerit().value() == 0);
					assert(!measure(encode(width,height,stride,format,1,false,0)).figureOfMerit());
					assert(!measure(encode(width,height,stride,format,1,false,1023)).figureOfMerit());
					assert(!measureBayerFocus(sharp.data(),10,width,height,stride,0,0,width,height,format).valid);
					assert(!measureBayerFocus(sharp.data(),sharp.size(),width,height,1,0,0,width,height,format).valid);
					assert(!measureBayerFocus(sharp.data(),sharp.size(),width,height,stride,width,0,4,height,format).valid);
					assert(!measureBayerFocus(sharp.data(),sharp.size(),width,height,stride,0,0,16,16,format).valid);
					assert(measureBayerFocus(sharp.data(),sharp.size(),width,height,stride,7,9,600,440,format).figureOfMerit().has_value());
					++cases;
				}
			}
		}
	}
	/* Exact CSI2/unpacked equivalence exercises all low-bit wire lanes. */
	for (unsigned int bits : {10U,12U}) {
		FocusBayerFormat unpacked{bits,false,false,false},packed{bits,true,false,false};
		auto a=encode(640,480,1280,unpacked),b=encode(640,480,640*bits/8,packed);
		assert(measureBayerFocus(a.data(),a.size(),640,480,1280,0,0,640,480,unpacked).figureOfMerit() ==
		       measureBayerFocus(b.data(),b.size(),640,480,640*bits/8,0,0,640,480,packed).figureOfMerit());
	}
	/* Unsupported format, incomplete packed group, extreme dimensions and null. */
	std::array<uint8_t,64> tiny{};
	assert(!measureBayerFocus(nullptr,64,4,4,16,0,0,4,4,{10,true,false,false}).valid);
	assert(!measureBayerFocus(tiny.data(),64,4,4,16,0,0,4,4,{14,true,false,false}).valid);
	assert(!measureBayerFocus(tiny.data(),64,21,21,32,0,0,20,20,{10,true,false,false}).valid);
	assert(!measureBayerFocus(tiny.data(),64,~0U,~0U,~0U,0,0,20,20,{12,false,false,false}).valid);
	std::cout << "{\"format_phase_cases\":" << cases << ",\"sanitized\":true,\"passed\":true}\n";
}
