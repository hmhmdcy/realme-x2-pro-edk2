/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <optional>
#include <linux/qcom-camss-config.h>
#include <libcamera/geometry.h>
#include "../libipa/lsc_resample.h"

namespace libcamera {
class ValueNode;
namespace ipa::camss {

int readLensShadingMesh(const ValueNode &value,LscMesh *mesh);
int readLensShadingMapping(const ValueNode &tuning,LscMapping *mapping);
int encodeLensShading(const LscMesh &source,const Size &input,const LscMapping &mapping,camss_params_lsc *parameters);

/* Static mode tuning. The ISP applies it once at stream start; colour-gain
 * updates do not repeatedly upload this mesh. Absence leaves LSC disabled.
 */
int configureLensShading(const ValueNode &tuning, const Size &input,
			 std::optional<camss_params_lsc> *parameters);

} /* namespace ipa::camss */
} /* namespace libcamera */
