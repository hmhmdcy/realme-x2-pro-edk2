/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <cerrno>
#include <cstdint>
#include <limits>
#include <memory>
#include <linux/qcom-camss-config.h>

namespace libcamera::ipa::camss {
/* Physical IFE state, independent from the IPE successful-history ledger.
 * A parameter DQ never calls accept(). Tokens retain immutable versions across
 * later IFE ACKs, IPE failures and buffer completion in a different order. */
template<class Math> class IfeGtmHistory {
public:
 struct Version {
  camss_params_ife_gtm parameters{};
  Math math{};
  uint32_t sourceSof = 0, revision = 0;
  uint64_t sourceHistogram = 0;
  bool ready = false;
 };
 using Pointer = std::shared_ptr<const Version>;
 void reset() { active_.reset();pending_.reset();serial_=generation_=0;bank_=status_=0; }
 int stage(Version version, uint32_t revision, Pointer *out)
 {
  if(!out)return -EINVAL;
  if(pending_)return -EBUSY;
  if(serial_==std::numeric_limits<uint64_t>::max())return -EOVERFLOW;
  version.parameters.cookie=++serial_;version.revision=revision;
  version.parameters.header={CAMSS_PARAMS_IFE_GTM,0,sizeof(camss_params_ife_gtm)};
  pending_=std::make_shared<const Version>(std::move(version));*out=pending_;return 0;
 }
 int accept(uint32_t sof,const camss_stats_ife_gtm &receipt,Pointer *out,bool *changed)
 {
  if(!out||!changed)return -EINVAL;
  *out={};*changed=false;
  if(!receipt.cookie||!receipt.generation||receipt.bank>1||
     (receipt.status!=1&&receipt.status!=3))return -EPROTO;
  if(active_&&receipt.cookie==active_->parameters.cookie) {
   if(receipt.generation!=generation_||receipt.bank!=bank_||receipt.status!=status_)return -EPROTO;
   *out=active_;return 0;
  }
  if(!pending_||receipt.cookie!=pending_->parameters.cookie)return -ESTALE;
  if(generation_==std::numeric_limits<uint64_t>::max()||receipt.generation!=generation_+1||
     receipt.status!=(1u|(pending_->parameters.enabled?2u:0u))||
     (pending_->ready&&sof<=pending_->sourceSof))return -EPROTO;
  active_=pending_;pending_.reset();generation_=receipt.generation;bank_=receipt.bank;status_=receipt.status;
  *out=active_;*changed=true;return 0;
 }
 const Pointer &active() const { return active_; }
 void cancelUnsubmitted(uint64_t cookie) { if(pending_&&pending_->parameters.cookie==cookie)pending_.reset(); }
 bool busy() const { return bool(pending_); }
 uint64_t generation() const { return generation_; }
private:
 Pointer active_,pending_;
 uint64_t serial_=0,generation_=0;
 uint32_t bank_=0,status_=0;
};
} /* namespace libcamera::ipa::camss */
