/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <cmath>
#include <cstdint>
#include <optional>

namespace libcamera::ipa::camss {

/* Convergence belongs to observed, applied WB gains, not to a GTM upload. */
class AppliedAwbStatus {
public:
 void reset() { locked_.reset(); }
 void observe(uint32_t sof, double red, double blue, bool valid, bool locked)
 {
  if (!valid || !locked || !std::isfinite(red) || !std::isfinite(blue) || red <= 0 || blue <= 0)
   return reset();
  locked_ = State{sof, red, blue};
 }
 bool locked(uint32_t sof, double red, double blue) const
 {
  return locked_ && sof >= locked_->sof && red == locked_->red && blue == locked_->blue;
 }
private:
 struct State { uint32_t sof; double red, blue; };
 std::optional<State> locked_;
};

} /* namespace libcamera::ipa::camss */
