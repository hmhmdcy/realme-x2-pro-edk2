/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <libcamera/ipa/camss_ipa_serializer.h>

using namespace libcamera;
int main()
{
 unsigned int cases = 0;
 for (uint32_t revision : {0u, 1u, 0x7fffffffu, 0xfffffffeu}) {
  ipa::camss::Statistics source{};
  source.status = -123; source.population = UINT64_C(0x0102030405060708);
  source.weightedSum = UINT64_C(0x8877665544332211);
  source.parametersKnown = true; source.sensorControlsKnown = true;
  source.automaticUpdate = {true, revision, 3332, 960};
  auto [bytes, fds] = IPADataSerializer<ipa::camss::Statistics>::serialize(source);
  assert(fds.empty());
  auto copy = IPADataSerializer<ipa::camss::Statistics>::deserialize(bytes);
  assert(copy.status == source.status && copy.population == source.population && copy.weightedSum == source.weightedSum);
  assert(copy.parametersKnown && copy.sensorControlsKnown && copy.automaticUpdate.valid);
  assert(copy.automaticUpdate.revision == revision && copy.automaticUpdate.exposureLines == 3332 && copy.automaticUpdate.gainCode == 960);
  auto [updateBytes, updateFds] = IPADataSerializer<ipa::camss::AutoSensorUpdate>::serialize(source.automaticUpdate);
  assert(updateFds.empty() && updateBytes.size() == 13 && updateBytes[0] == 1);
  const uint32_t expected[]{revision, 3332, 960};
  assert(!std::memcmp(updateBytes.data() + 1, expected, 12));
  ++cases;
 }
 std::cout << "SERIALIZER_PASS cases=" << cases << " update_bytes=13 independent_field_layout=pass" << std::endl;
}
