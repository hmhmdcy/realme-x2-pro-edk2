/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc_input.h"
#include "../kernel415/libipa/tmc_runtime.h"
#include "../kernel414/libipa/tmc11_tree.h"
#include "../kernel413/libipa/tmc11_generation.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
using namespace libcamera::ipa;
struct Reader {
	const std::vector<unsigned char> &bytes; size_t offset = 0;
	template<typename T> T get() {
		if (offset + sizeof(T) > bytes.size()) throw std::runtime_error("truncated");
		T value; std::memcpy(&value, bytes.data() + offset, sizeof(T)); offset += sizeof(T); return value;
	}
	uint32_t count() { auto n = get<uint32_t>(); if (!n || n > 20) throw std::runtime_error("count"); return n; }
};
struct Output {
	Tmc11PolicyResult policy;
	TargetAdrcMetadata adrc, cache;
	uint32_t version;
	TmcLtmDecision ltm;
};
static_assert(sizeof(Output) == 8544 && sizeof(Tmc11Region) == 176);
bool evaluate(Reader &r, Output *output)
{
	auto policyInput = r.get<Tmc11PolicyInput>(); auto reserve = r.get<std::array<uint32_t, 4>>();
	auto propertyPresent = r.get<uint32_t>(); auto gamma = r.get<std::array<float, 257>>();
	auto weights = r.get<std::array<float, 1024>>();
	auto newHistogram = r.get<std::array<uint32_t, 1024>>(), oldHistogram = r.get<std::array<uint32_t, 1024>>();
	Output result{}; result.adrc = r.get<TargetAdrcMetadata>(); result.cache = r.get<TargetAdrcMetadata>();
	auto root10 = r.get<std::array<uint32_t, 3>>();
	auto ac = r.get<uint32_t>(), hc = r.get<uint32_t>(); auto triggers = r.get<Tmc11TreeTriggers>();
	std::vector<Tmc11DrcRegion> tree(r.count());
	for (auto &drc : tree) {
		drc.trigger = r.get<std::array<float, 2>>(); drc.children.resize(r.count());
		for (auto &hdr : drc.children) {
			hdr.trigger = r.get<std::array<float, 6>>(); hdr.children.resize(r.count());
			for (auto &aec : hdr.children) aec = r.get<Tmc11AecRegion>();
		}
	}
	if (r.offset != r.bytes.size() || propertyPresent > 1 || reserve[2] != 2 || reserve[3] != 5 ||
	    !evaluateTmc11Policy(policyInput, &result.policy)) return false;
	if (result.policy.calculate) {
		Tmc11RegionValues values; Tmc11Region region; Tmc11GenerationResult generated;
		/* The caller supplies the selected cached root and leased old/new statistics. */
		if (!interpolateTmc11Tree(tree, ac, hc, triggers, &values)) return false;
		std::memcpy(&region, values.data(), sizeof(region));
		const auto *histogram = result.policy.histogramSource == 2 ? &newHistogram :
					result.policy.histogramSource == 1 ? &oldHistogram : nullptr;
		if (!generateTmc11Curve(region, triggers.drcGain, policyInput.newTriggers[1], gamma, weights, histogram, &generated)) return false;
		auto store = [&](size_t at, const auto &value) { std::memcpy(result.adrc.data() + at, &value, sizeof(value)); };
		store(0, uint32_t(1)); store(4, uint32_t(1)); store(8, reserve[0]); store(12, reserve[1]);
		store(16, generated.pchip.x); store(36, generated.pchip.y); store(56, generated.darkGain);
		store(60, generated.gtmPercentage); store(64, generated.ltm.percentage);
		store(92, generated.pchip.coefficient); store(128, generated.contrastCurve);
		store(4224, reserve[2]); store(4228, generated.ltm.bright); store(4232, generated.ltm.dark);
	}
	if (!updateTargetAdrcMetadata(propertyPresent ? &result.adrc : nullptr, &result.cache)) return false;
	uint32_t cacheVersion, ltmEnable;
	std::memcpy(&cacheVersion, result.cache.data() + 4, 4); std::memcpy(&ltmEnable, result.cache.data() + 12, 4);
	result.version = bindTargetIpeTmcVersion(cacheVersion, 0);
	if (!selectTargetTmcLtmSource({ root10[0], root10[1], root10[2], result.version, 1, ltmEnable, 0 }, &result.ltm)) return false;
	*output = result; return true;
}
int main()
{
	uint32_t size;
	while (std::fread(&size, 4, 1, stdin) == 1) {
		if (size > 2000000) return 2;
		std::vector<unsigned char> bytes(size);
		if (std::fread(bytes.data(), size, 1, stdin) != 1) return 3;
		auto saved = bytes; Output output; std::memset(&output, 0xa5, sizeof(output)); uint32_t status;
		try { Reader reader{ bytes }; status = evaluate(reader, &output); } catch (const std::runtime_error &) { return 4; }
		assert(bytes == saved);
		if (!status) { unsigned char expected[sizeof(output)]; std::memset(expected, 0xa5, sizeof(expected)); assert(!std::memcmp(&output, expected, sizeof(output))); }
		assert(std::fwrite(&status, 4, 1, stdout) == 1 && std::fwrite(&output, sizeof(output), 1, stdout) == 1);
	}
	return std::ferror(stdin) || std::ferror(stdout);
}
