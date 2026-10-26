/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <cassert>
#include <limits>
#include "awb_status.h"
using libcamera::ipa::camss::AppliedAwbStatus;
int main()
{
 AppliedAwbStatus state;
 assert(!state.locked(0,1,1));
 state.observe(10,1.5,2,true,true);
 assert(!state.locked(9,1.5,2));
 assert(state.locked(10,1.5,2)&&state.locked(20,1.5,2));
 assert(!state.locked(20,1.5078125,2)&&!state.locked(20,1.5,1.9921875));
 state.observe(21,1.5,2,true,false);assert(!state.locked(22,1.5,2));
 state.observe(23,1.5,2,true,true);state.observe(24,1.5,2,false,true);assert(!state.locked(25,1.5,2));
 state.observe(26,1.5,2,true,true);state.reset();assert(!state.locked(27,1.5,2));
 state.observe(28,std::numeric_limits<double>::quiet_NaN(),2,true,true);assert(!state.locked(29,1.5,2));
}
