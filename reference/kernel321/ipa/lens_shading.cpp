/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "lens_shading.h"

#include <array>
#include <cerrno>
#include <cmath>

#include "libcamera/internal/yaml_parser.h"
#include "../libipa/lens_shading.h"
#include "../libipa/lsc_resample.h"

namespace libcamera::ipa::camss {

static int readPair(const ValueNode &value, double *a, double *b)
{
	if (!value.isList() || value.size() != 2)
		return -EINVAL;
	auto x = value[0].get<double>(), y = value[1].get<double>();
	if (!x || !y || !std::isfinite(*x) || !std::isfinite(*y))
		return -EINVAL;
	*a = *x; *b = *y;
	return 0;
}

static int readMesh(const ValueNode &value, LscMesh *mesh)
{
	static constexpr std::array<const char *, 4> names = { "r", "gr", "gb", "b" };
	if (!value.isDictionary())
		return -EINVAL;
	for (unsigned int c = 0; c < LscChannels; ++c) {
		const auto &channel = value[names[c]];
		if (!channel.isList() || channel.size() != LscPoints)
			return -EINVAL;
		for (unsigned int i = 0; i < LscPoints; ++i) {
			auto number = channel[i].get<float>();
			if (!number || !std::isfinite(*number) || *number <= 0)
				return -EINVAL;
			(*mesh)[c][i] = *number;
		}
	}
	return 0;
}

int configureLensShading(const ValueNode &tuning, const Size &input,
			 std::optional<camss_params_lsc> *parameters)
{
	if (!parameters)
		return -EINVAL;
	parameters->reset();
	if (tuning.isEmpty())
		return 0;
	if (!tuning.isDictionary())
		return -EINVAL;
	if (!tuning["enabled"].isEmpty()) {
		auto enabled = tuning["enabled"].get<bool>();
		if (!enabled)
			return -EINVAL;
		if (!*enabled)
			return 0;
	}

	LscMapping mapping;
	if (readPair(tuning["source_span"], &mapping.sourceSpanX, &mapping.sourceSpanY) ||
	    readPair(tuning["first_quad"], &mapping.firstX, &mapping.firstY) ||
	    readPair(tuning["quad_step"], &mapping.stepX, &mapping.stepY))
		return -EINVAL;
	LscGrid grid;
	LscMesh source, resampled;
	if (!lscGridForSize(input.width, input.height, &grid) ||
	    readMesh(tuning["gains"], &source))
		return -EINVAL;
	if (!tuning["golden"].isEmpty() || !tuning["unit"].isEmpty()) {
		LscMesh golden, unit, factors, calibrated;
		if (readMesh(tuning["golden"], &golden) || readMesh(tuning["unit"], &unit) ||
		    !lscCalibrationFactors(golden, unit, &factors) ||
		    !lscApplyCalibration(source, factors, &calibrated))
			return -EINVAL;
		source = calibrated;
	}
	LscPackedMesh packed;
	if (!lscResample(source, grid, mapping, &resampled) ||
	    !lscPackTitan17x(resampled, &packed))
		return -EINVAL;

	camss_params_lsc result{};
	static_assert(sizeof(result) == 1792);
	result.header = { CAMSS_PARAMS_LSC, V4L2_ISP_PARAMS_FL_BLOCK_ENABLE, sizeof(result) };
	result.cell_width = grid.cellWidth; result.cell_height = grid.cellHeight;
	result.x_start = grid.xStart; result.y_start = grid.yStart;
	result.subdivision = grid.subdivision;
	for (unsigned int i = 0; i < LscPoints; ++i) {
		result.gains[LscR][i] = packed.grr[i] & 8191;
		result.gains[LscGr][i] = packed.grr[i] >> 13;
		result.gains[LscGb][i] = packed.gbb[i] >> 13;
		result.gains[LscB][i] = packed.gbb[i] & 8191;
	}
	*parameters = result;
	return 0;
}

} /* namespace libcamera::ipa::camss */
