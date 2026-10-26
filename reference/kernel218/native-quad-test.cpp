/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "native_quad_bayer.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <thread>

using libcamera::NativeQuadBayer;
using RGB = std::array<uint16_t, 3>;

static void require(bool condition, const char *message)
{
	if (!condition)
		throw std::runtime_error(message);
}

static unsigned int colour(unsigned int x, unsigned int y, unsigned int rx, unsigned int ry)
{
	if (((x / 2) % 2 == rx) != ((y / 2) % 2 == ry))
		return 1;
	return (x / 2) % 2 == rx ? 0 : 2;
}

static std::vector<uint8_t> pack(const std::vector<uint16_t> &raw, unsigned int w,
				 unsigned int h, unsigned int stride)
{
	std::vector<uint8_t> bytes(size_t(h) * stride, 0xe7);
	for (unsigned int y = 0; y < h; y++)
		for (unsigned int x = 0; x < w; x++) {
			const uint16_t v = raw[size_t(y) * w + x];
			const size_t group = size_t(y) * stride + size_t(x / 4) * 5;
			bytes[group + x % 4] = v >> 2;
			const unsigned int shift = (x % 4) * 2;
			bytes[group + 4] = (bytes[group + 4] & ~(3 << shift)) | ((v & 3) << shift);
		}
	return bytes;
}

/* Independent oracle: find nearest same-colour coordinates by scanning the
 * complete axis, then use floating point interpolation, not production phase
 * offsets, weights, row cache, or RAW unpacking. */
static std::array<unsigned int, 2> bounds(unsigned int position, unsigned int n,
					 unsigned int wanted)
{
	int before = -1, after = -1;
	for (unsigned int i = 0; i < n; i++) {
		if ((i / 2) % 2 != wanted)
			continue;
		if (i <= position)
			before = i;
		if (i >= position && after < 0)
			after = i;
	}
	if (before < 0)
		before = after;
	if (after < 0)
		after = before;
	return { unsigned(before), unsigned(after) };
}

static double lerp(unsigned int x, std::array<unsigned int, 2> axis, double a, double b)
{
	if (axis[0] == axis[1])
		return a;
	const double t = double(x - axis[0]) / (axis[1] - axis[0]);
	return a * (1 - t) + b * t;
}

static RGB expected(const std::vector<uint16_t> &raw, unsigned int w, unsigned int h,
		    unsigned int x, unsigned int y, unsigned int rx, unsigned int ry)
{
	auto at = [&](unsigned int a, unsigned int b) { return raw[size_t(b) * w + a]; };
	RGB rgb;
	for (unsigned int c : { 0U, 2U }) {
		const auto xx = bounds(x, w, c ? 1 - rx : rx);
		const auto yy = bounds(y, h, c ? 1 - ry : ry);
		const double top = lerp(x, xx, at(xx[0], yy[0]), at(xx[1], yy[0]));
		const double bottom = lerp(x, xx, at(xx[0], yy[1]), at(xx[1], yy[1]));
		rgb[c] = std::floor(lerp(y, yy, top, bottom) + 0.500000001);
	}
	if (colour(x, y, rx, ry) == 1) {
		rgb[1] = at(x, y);
	} else {
		const auto xx = bounds(x, w, 1 - (x / 2) % 2);
		const auto yy = bounds(y, h, 1 - (y / 2) % 2);
		rgb[1] = std::floor((lerp(x, xx, at(xx[0], y), at(xx[1], y)) +
				     lerp(y, yy, at(x, yy[0]), at(x, yy[1]))) / 2 + 0.500000001);
	}
	return rgb;
}

static size_t check(const std::vector<uint16_t> &raw, unsigned int w, unsigned int h,
		    unsigned int rx, unsigned int ry, bool constant, bool affine)
{
	const unsigned int stride = w / 4 * 5 + 11; /* poison row padding */
	const auto bytes = pack(raw, w, h, stride);
	NativeQuadBayer decoder;
	require(decoder.configure(w, h, stride, rx, ry), "configure valid");
	NativeQuadBayer::Workspace work;
	std::vector<RGB> output(size_t(w) * h, { 65535, 65535, 65535 });
	std::vector<unsigned int> visits(output.size());
	auto sink = [&](unsigned int x, unsigned int y, RGB rgb) {
		require(x < w && y < h, "output coordinate");
		output[size_t(y) * w + x] = rgb;
		visits[size_t(y) * w + x]++;
	};
	/* Non-four-aligned partitions exercise every thread boundary phase. */
	for (unsigned int y = 0; y < h;) {
		const unsigned int end = std::min(h, y + 3);
		require(decoder.processRows(bytes.data(), bytes.size(), y, end, work, sink), "process range");
		y = end;
	}
	for (unsigned int y = 0; y < h; y++)
		for (unsigned int x = 0; x < w; x++) {
			const size_t i = size_t(y) * w + x;
			require(visits[i] == 1, "each physical pixel exactly once");
			require(output[i] == expected(raw, w, h, x, y, rx, ry), "independent oracle");
			require(output[i][colour(x, y, rx, ry)] == raw[i], "measured channel/LSB lost");
			if (constant)
				require(output[i] == RGB({ 117, 527, 933 }), "constant colour, border/order");
			if (affine && x >= 2 && x < w - 2 && y >= 2 && y < h - 2)
				for (unsigned int c = 0; c < 3; c++)
					require(output[i][c] == 100 + 200 * c + 2 * x + 3 * y, "affine plane");
		}
	bool called = false;
	auto noSink = [&](unsigned int, unsigned int, RGB) { called = true; };
	require(!decoder.processRows(bytes.data(), bytes.size() - 1, 0, h, work, noSink), "short input rejected");
	require(!decoder.processRows(bytes.data(), bytes.size(), h, h + 1, work, noSink), "bad range rejected");
	require(!called, "invalid input emitted pixels");
	return output.size();
}

int main(int argc, char **argv)
try {
	std::mt19937 random(218);
	size_t checked = 0, cases = 0;
	NativeQuadBayer invalid;
	require(!invalid.configure(0, 4, 5, 0, 0), "zero size");
	require(!invalid.configure(6, 4, 10, 0, 0), "bad phase size");
	require(!invalid.configure(4, 4, 4, 0, 0), "short stride");
	require(!invalid.configure(4, 4, 5, 2, 0), "bad CFA order");
	for (unsigned int rx = 0; rx < 2; rx++)
		for (unsigned int ry = 0; ry < 2; ry++)
			for (unsigned int w : { 4U, 8U, 12U, 20U, 28U })
				for (unsigned int h : { 4U, 8U, 12U, 20U })
					for (unsigned int pattern = 0; pattern < 5; pattern++) {
						std::vector<uint16_t> raw(size_t(w) * h);
						for (unsigned int y = 0; y < h; y++)
							for (unsigned int x = 0; x < w; x++) {
								const unsigned int c = colour(x, y, rx, ry);
								uint16_t value = random() & 1023;
								if (pattern == 0) value = RGB({ 117, 527, 933 })[c];
								if (pattern == 1) value = 100 + 200 * c + 2 * x + 3 * y;
								if (pattern == 2) value = (x + y) % 4; /* LSB only */
								if (pattern == 3) value = (x == w / 2 && y == h / 2) ? 1023 : 0;
								raw[size_t(y) * w + x] = value;
							}
						checked += check(raw, w, h, rx, ry, pattern == 0, pattern == 1);
						cases++;
					}
	std::cout << "{\"cases\":" << cases << ",\"oracle_pixels\":" << checked
		  << ",\"all_four_orders\":true,\"native_samples_exact\":true,\"padding_and_borders\":true";
	if (argc > 1 && std::string(argv[1]) == "--full") {
		const unsigned int w = 4608, h = 3456, stride = 5760;
		std::vector<uint16_t> raw(size_t(w) * h);
		for (size_t i = 0; i < raw.size(); i++) raw[i] = (i * 13 + i / w * 7) % 1024;
		const auto bytes = pack(raw, w, h, stride);
		NativeQuadBayer decoder;
		require(decoder.configure(w, h, stride, 0, 0), "full configure");
		std::vector<uint8_t> output(size_t(w) * h * 3);
		std::vector<double> elapsed;
		for (unsigned int iteration = 0; iteration < 3; iteration++) {
			const auto start = std::chrono::steady_clock::now();
			std::array<std::thread, 4> threads;
			for (unsigned int i = 0; i < threads.size(); i++)
				threads[i] = std::thread([&, i]() {
					NativeQuadBayer::Workspace work;
					require(decoder.processRows(bytes.data(), bytes.size(), i * h / 4, (i + 1) * h / 4,
						work, [&](unsigned int x, unsigned int y, RGB rgb) {
							require(rgb[colour(x, y, 0, 0)] == raw[size_t(y) * w + x], "full native sample");
							for (unsigned int c = 0; c < 3; c++)
								output[(size_t(y) * w + x) * 3 + c] = rgb[c] >> 2;
						}), "full process");
				});
			for (auto &thread : threads) thread.join();
			elapsed.push_back(std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count());
		}
		std::cout << ",\"full_size\":[4608,3456],\"full_output_bytes\":" << output.size()
			  << ",\"four_thread_ms\":[" << elapsed[0] << ',' << elapsed[1] << ',' << elapsed[2] << ']';
	}
	std::cout << ",\"passed\":true}\n";
	return 0;
} catch (const std::exception &e) {
	std::cerr << e.what() << '\n';
	return 1;
}
