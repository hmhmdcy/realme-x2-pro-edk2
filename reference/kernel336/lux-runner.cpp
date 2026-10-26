/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/aec_lux.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <limits>
using namespace libcamera::ipa;
template<class T> static T read(FILE *file) {T value;assert(fread(&value,sizeof(value),1,file)==1);return value;}
int main(int argc,char **argv)
{
 assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
 AecLuxIndex model;
 uint32_t mode;while(fread(&mode,4,1,in)==1) {
  bool valid=false;float a=0,b=0;
  if(mode==1 || mode==2){
   AecExposureAnchor anchor;anchor.gain=read<float>(in);anchor.exposureTimeNs=read<uint64_t>(in);anchor.index=read<float>(in);
   float gainOrCorrection=read<float>(in);
   if(mode==1)valid=aecManualExposureIndex(anchor,gainOrCorrection,read<uint64_t>(in),&a);
   else valid=aecSensitivityExposureIndex(anchor,gainOrCorrection,read<float>(in),&a);
  }else if(mode==3){
   AecLuxIndex::Configuration configuration;configuration.compensate=read<uint32_t>(in);configuration.referenceZeroSensitivity=read<float>(in);configuration.tableZeroSensitivity=read<float>(in);configuration.filterFactor=read<float>(in);
   valid=model.configure(configuration);
  }else if(mode==4){
   float index=read<float>(in),luma=read<float>(in);bool reset=read<uint32_t>(in);
   valid=model.calculate(index,luma,&a,reset);
  }else if(mode==5){
   float index=read<float>(in);bool reset=read<uint32_t>(in);std::array<float,256> cells;
   assert(fread(cells.data(),sizeof(cells),1,in)==1);
   valid=aecUniformLuxLuma(cells,&b)&&model.calculate(index,b,&a,reset);
  }else return 3;
  assert(valid);uint32_t status=valid;assert(fwrite(&status,4,1,out)==1&&fwrite(&a,4,1,out)==1&&fwrite(&b,4,1,out)==1);
 }
 float value=0;AecExposureAnchor invalid{0,0,0};
 assert(!aecManualExposureIndex(invalid,1,1,&value)&&!aecSensitivityExposureIndex(invalid,1,1,&value));
 AecExposureAnchor anchor{1,10000,0};
 assert(!aecManualExposureIndex(anchor,-1,1,&value)&&!aecSensitivityExposureIndex(anchor,0,1,&value));
 assert(!model.calculate(0,0,&value)&&!model.calculate(std::numeric_limits<float>::quiet_NaN(),50,&value));
 assert(!model.configure({true,0,1,.5f})&&!model.configure({false,0,0,-.1f}));
 std::array<float,256> cells{};cells[4]=256;assert(!aecUniformLuxLuma(cells,&value));
 fclose(in);return fclose(out)?4:0;
}
