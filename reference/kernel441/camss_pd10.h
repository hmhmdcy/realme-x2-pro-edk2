/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <optional>
#include <libcamera/geometry.h>

namespace libcamera {

struct CamssPd10Layout {
	Size size;
	unsigned int stride, sliceHeight, frameSize;
};

/* Retained SM8150 allocation: even quarter, 192-byte packed rows, four rows. */
inline std::optional<CamssPd10Layout> camssPd10Layout(const Size &full)
{
	if (full.width < 128 || full.height < 128 || full.width > 8192 ||
	    full.height > 8192 || ((full.width | full.height) & 1))
		return std::nullopt;
	CamssPd10Layout layout;
	layout.size = { ((full.width + 7) / 4) & ~1U, ((full.height + 7) / 4) & ~1U };
	layout.stride = ((layout.size.width * 4 + 191) / 192) * 192;
	layout.sliceHeight = ((layout.size.height + 7) / 8) * 4;
	layout.frameSize = layout.stride * layout.sliceHeight;
	return layout;
}

} /* namespace libcamera */
