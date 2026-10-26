/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ipe_numeric_history.h"
#include <array>
#include <cassert>
#include <cstdio>
using namespace libcamera::ipa::camss;
struct State { std::array<float, 65> curve{}; unsigned updates = 0; };
int main()
{
	IpeNumericHistory<State> h; State next{}; next.curve[64] = 1; next.updates = 90;
	assert(h.prepare(1, 1, 1, 0, next) == -ESTALE);
	assert(h.start(1) && !h.start(2));
	assert(!h.prepare(1, 1, 1, 0, next));
	assert(h.revision() == 0 && h.state().updates == 0 && h.pending()->next.updates == 90);
	/* Observations 2 and 3 may complete out of order, but neither was used
	 * as the calculation's base and neither can resolve its numerical state. */
	assert(h.prepare(1, 2, 2, 0, next) == -EBUSY);
	assert(h.resolve(1, 3, 3, true) == -ENOENT && h.busy());
	assert(h.resolve(1, 2, 1, true) == -ESTALE && h.busy());
	assert(h.resolve(1, 1, 1, false) == 0 && !h.busy() && h.revision() == 0);
	assert(h.state().updates == 0);
	assert(!h.prepare(1, 2, 4, 0, next));
	assert(h.resolve(1, 2, 4, true) == 1 && h.revision() == 1 && h.state().updates == 90);
	assert(h.resolve(1, 2, 4, true) == -ENOENT);
	assert(h.prepare(1, 3, 5, 0, next) == -ESTALE);
	assert(h.prepare(1, 1, 5, 1, next) == -EALREADY);
	next.updates = 89; assert(!h.prepare(1, 3, 5, 1, next));
	assert(h.state().updates == 90); h.stop();
	assert(!h.busy() && h.resolve(1, 3, 5, true) == -ESTALE);
	assert(!h.start(1) && h.start(2) && h.revision() == 0 && h.state().updates == 0);
	assert(h.prepare(1, 4, 6, 0, next) == -ESTALE);
	assert(h.prepare(2, 1, 5, 0, next) == -EALREADY);
	assert(!h.prepare(2, 1, 6, 0, next));
	assert(h.resolve(1, 1, 6, true) == -ESTALE && h.busy());
	assert(h.resolve(2, 1, 6, true) == 1 && h.state().updates == 89);
	std::puts("scenarios=12 passed=1");
}
