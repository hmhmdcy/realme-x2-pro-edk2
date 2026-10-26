/* Verify the production helper against the production legacy codec on ARM. */
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <tuple>
#include <vector>
#include "libcamera/internal/camss_byte_serializer.h"
#include "libcamera/internal/ipa_data_serializer.h"

int main()
{
 using Codec=libcamera::IPADataSerializer<std::vector<uint8_t>>;
 for (size_t size : {size_t(0),size_t(1),size_t(16),size_t(256),size_t(6008)}) {
  std::vector<uint8_t> input(size);
  for(size_t i=0;i<size;++i)input[i]=uint8_t(i*37+size*13);
  auto legacy=Codec::serialize(input);
  auto fast=libcamera::camssSerializeByteVector(input);
  assert(std::get<0>(legacy)==std::get<0>(fast));
  assert(std::get<1>(legacy).empty() && std::get<1>(fast).empty());
  assert(std::get<0>(fast).size()==4+9*size);
  assert(Codec::deserialize(std::get<0>(fast),std::get<1>(fast))==input);
  std::printf("WIRE bytes=%zu encoded=%zu old-decode=1 equal=1\n",size,std::get<0>(fast).size());
 }
 return 0;
}
