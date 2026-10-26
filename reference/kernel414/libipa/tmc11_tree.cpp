/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "tmc11_tree.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace libcamera::ipa {
namespace {
template<size_t N> bool finite(const std::array<float, N> &values)
{
	return std::all_of(values.begin(), values.end(), [](float v) { return std::isfinite(v); });
}
template<size_t N> bool intervals(const std::array<float, N> &values)
{
	if (!finite(values))
		return false;
	for (size_t i = 0; i < N; i += 2)
		if (values[i] > values[i + 1])
			return false;
	return true;
}
bool validate(const std::vector<Tmc11DrcRegion> &tree)
{
	/* The target search helper has space for twenty trigger intervals. */
	if (tree.empty() || tree.size() > 20)
		return false;
	for (const auto &drc : tree) {
		if (!intervals(drc.trigger) || drc.children.empty() || drc.children.size() > 20)
			return false;
		for (const auto &hdr : drc.children) {
			if (!intervals(hdr.trigger) || hdr.children.empty() || hdr.children.size() > 20)
				return false;
			for (const auto &aec : hdr.children)
				if (!intervals(aec.trigger) || !finite(aec.data))
					return false;
		}
	}
	return true;
}
struct Selection { size_t left, right; float ratio; };
template<typename Regions> Selection select(const Regions &regions, size_t axis, float trigger)
{
	for (size_t i = 0; i < regions.size(); ++i) {
		if (trigger <= regions[i].trigger[axis + 1])
			return { i, i, 0 };
		if (i + 1 < regions.size() && trigger < regions[i + 1].trigger[axis]) {
			double left = regions[i].trigger[axis + 1];
			double right = regions[i + 1].trigger[axis];
			return { i, i + 1, float((double(trigger) - left) / (right - left)) };
		}
	}
	return { regions.size() - 1, regions.size() - 1, 0 };
}
bool blend(const Tmc11RegionValues &a, const Tmc11RegionValues &b, float ratio,
	   Tmc11RegionValues *output)
{
	if (ratio <= 0) { *output = a; return true; }
	if (ratio >= 1) { *output = b; return true; }
	for (size_t i = 0; i < a.size(); ++i) {
		if (double(a[i]) < std::numeric_limits<int32_t>::min() ||
		    double(a[i]) > std::numeric_limits<int32_t>::max() ||
		    double(b[i]) < std::numeric_limits<int32_t>::min() ||
		    double(b[i]) > std::numeric_limits<int32_t>::max())
			return false;
		int32_t ai = int32_t(a[i]), bi = int32_t(b[i]);
		int64_t difference = int64_t(bi) - ai;
		if (difference < std::numeric_limits<int32_t>::min() ||
		    difference > std::numeric_limits<int32_t>::max())
			return false;
		double af = double(a[i] - float(ai)) * 1000000.0;
		double bf = double(b[i] - float(bi)) * 1000000.0;
		volatile double fractionalStep = double(ratio) * (bf - af);
		float fraction = float(af + fractionalStep) / 1000000.0f;
		volatile double integerStep = double(ratio) * float(difference);
		float integer = float(double(ai) + integerStep);
		(*output)[i] = fraction + integer;
	}
	return finite(*output);
}
bool aec(const std::vector<Tmc11AecRegion> &regions, size_t axis, float trigger,
	 Tmc11RegionValues *output)
{
	const auto s = select(regions, axis, trigger);
	return blend(regions[s.left].data, regions[s.right].data, s.ratio, output);
}
bool hdr(const std::vector<Tmc11HdrRegion> &regions, size_t axis, float trigger,
	 size_t aecAxis, float aecTrigger, Tmc11RegionValues *output)
{
	const auto s = select(regions, axis, trigger);
	Tmc11RegionValues left, right;
	if (!aec(regions[s.left].children, aecAxis, aecTrigger, &left))
		return false;
	if (s.left == s.right) { *output = left; return true; }
	return aec(regions[s.right].children, aecAxis, aecTrigger, &right) &&
	       blend(left, right, s.ratio, output);
}
} /* namespace */
bool interpolateTmc11Tree(const std::vector<Tmc11DrcRegion> &tree,
			 uint32_t aecControl, uint32_t hdrControl,
			 const Tmc11TreeTriggers &triggers, Tmc11RegionValues *output)
{
	std::array<float, 5> inputs{ triggers.drcGain, triggers.realGain, triggers.luxIndex,
				    triggers.module88, triggers.module92 };
	if (!output || aecControl > 1 || hdrControl > 2 || !finite(inputs) || !validate(tree))
		return false;
	float hdrTrigger = hdrControl == 0 ? triggers.module88 : hdrControl == 1 ? triggers.module92 : 0;
	float aecTrigger = aecControl ? triggers.realGain : triggers.luxIndex;
	const auto s = select(tree, 0, triggers.drcGain);
	Tmc11RegionValues left, right, result;
	if (!hdr(tree[s.left].children, hdrControl * 2, hdrTrigger, aecControl * 2, aecTrigger, &left))
		return false;
	if (s.left == s.right) {
		result = left;
	} else if (!hdr(tree[s.right].children, hdrControl * 2, hdrTrigger, aecControl * 2, aecTrigger, &right) ||
		   !blend(left, right, s.ratio, &result)) {
		return false;
	}
	*output = result;
	return true;
}
} /* namespace libcamera::ipa */
