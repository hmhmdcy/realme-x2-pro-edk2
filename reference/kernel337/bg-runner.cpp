/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/aec_bayer_luma.h"
#include "libipa/aec_lux.h"
#include <cassert>
#include <cstdio>
#include <limits>
using namespace libcamera::ipa;
template<class T> static T read(FILE *file){T value;assert(fread(&value,sizeof(value),1,file)==1);return value;}
template<class T> static void write(FILE *file,const T &value){assert(fwrite(&value,sizeof(value),1,file)==1);}
static AecBayerLumaConfiguration configuration(FILE *file)
{
 AecBayerLumaConfiguration c;c.pixelsPerChannel=read<uint32_t>(file);c.inputBits=read<uint32_t>(file);
 c.highThreshold=read<std::array<uint32_t,4>>(file);c.weights=read<std::array<float,3>>(file);c.normalization=read<float>(file);return c;
}
int main(int argc,char **argv)
{
 assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
 uint32_t mode;
 while(fread(&mode,4,1,in)==1){
  if(mode==1){
   auto base=read<std::array<float,3>>(in),reference=read<std::array<float,3>>(in),current=read<std::array<float,3>>(in);
   bool enabled=read<uint32_t>(in);std::array<float,3> weights;
   assert(aecLumaWeights(base,reference,current,enabled,&weights));write(out,weights);
  }else if(mode==2){
   auto c=configuration(in);auto region=read<AecBayerRegion>(in);AecLumaCell result;
   assert(aecBayerRegionLuma(c,region,&result));write(out,result);
  }else if(mode==3){
   auto c=configuration(in);unsigned columns=read<uint32_t>(in),rows=read<uint32_t>(in);
   std::vector<AecLumaCell> regions;
   for(unsigned i=0;i<columns*rows;i++){auto region=read<AecBayerRegion>(in);AecLumaCell result;assert(aecBayerRegionLuma(c,region,&result));regions.push_back(result);}
   std::array<AecLumaCell,256> grid;assert(aecLegacyLumaGrid(regions,columns,rows,&grid));write(out,grid);
   std::array<float,256> values;for(unsigned i=0;i<256;i++)values[i]=grid[i].luma;
   float luma,index;AecLuxIndex model;assert(model.configure({false,0,0,0})&&aecUniformLuxLuma(values,&luma)&&model.calculate(200,luma,&index));write(out,index);write(out,luma);
  }else return 2;
 }
 AecBayerLumaConfiguration c{625,{16383,16383,16383,16383},14,{.2988f,.5869f,.1137f},1};
 AecBayerRegion bad{{1,0,0,0},{0,0,0,0}};AecLumaCell cell;
 assert(!aecBayerRegionLuma(c,bad,&cell));bad={{0,0,0,0},{626,0,0,0}};assert(!aecBayerRegionLuma(c,bad,&cell));
 c.normalization=0;assert(!aecBayerRegionLuma(c,{},&cell));
 std::array<AecLumaCell,256> grid;assert(!aecLegacyLumaGrid(std::vector<AecLumaCell>(768),32,24,&grid));
 assert(!aecLegacyLumaGrid(std::vector<AecLumaCell>(511),32,16,&grid));
 std::array<float,256> cells;cells.fill(300);float value;assert(aecUniformLuxLuma(cells,&value)&&value==300);
 cells[7]=std::numeric_limits<float>::quiet_NaN();assert(!aecUniformLuxLuma(cells,&value));
 fclose(in);return fclose(out)?3:0;
}
