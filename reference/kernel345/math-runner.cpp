// SPDX-License-Identifier: LGPL-2.1-or-later
#include "aec_exposure_table.h"
#include <cstdint>
#include <fstream>
#include <vector>
using namespace libcamera::ipa;
template<typename T> bool read(std::istream &s,T *value){return bool(s.read(reinterpret_cast<char*>(value),sizeof(T)));}
template<typename T> void write(std::ostream &s,const T &value){s.write(reinterpret_cast<const char*>(&value),sizeof(T));}
int main(int argc,char **argv)
{
 if(argc!=3)return 2;
 std::ifstream input(argv[1],std::ios::binary);std::ofstream output(argv[2],std::ios::binary);
 uint32_t count;if(!read(input,&count)||!output)return 2;
 for(uint32_t i=0;i<count;i++) {
  float index;uint32_t size;if(!read(input,&index)||!read(input,&size))return 2;
  std::vector<AecExposureKnee> knees;
  for(uint32_t j=0;j<size;j++) {
   AecExposureKnee knee;uint32_t priority;
   if(!read(input,&knee.gain)||!read(input,&knee.exposureTimeNs)||!read(input,&priority)||!read(input,&knee.index))return 2;
   knee.priority=static_cast<AecExposurePriority>(priority);knees.push_back(knee);
  }
  AecExposureTable table;AecExposureAllocation result{};
  uint32_t valid=table.configure(knees)&&table.allocate(index,&result);
  write(output,valid);write(output,result.gain);write(output,result.exposureTimeNs);write(output,result.index);
 }
 return output?0:3;
}
