// Generic module descriptors preserve UID/name/mode; payload parsing is reused
// from the earlier independent decoders rather than generating every IQ class.
#include "parametersetmanager.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

class Generic : public ParameterModule {
public:
 Generic(const char *name,VersionUnion version,UINT32 id,ModeUnion mode)
  :ParameterModule(name,version,id,mode) {}
 ParameterModule *Parse(ParameterFileSymbolTableEntry *entry,UINT64) const override {
  auto *result=new Generic(entry->Type,entry->Version,entry->ModeId,entry->Mode);
  result->ID=entry->ID;return result;
 }
};
class Manager : public ParameterSetManager {
 Generic prototype{"generic",VersionUnion(1,0,0),0,ModeUnion(0)};
 const ParameterModule *GetDefaultModule(char *) override {return &prototype;}
};
int main(int argc,char **argv) {
 if(argc!=2)return 2;
 std::ifstream input(argv[1],std::ios::binary);if(!input)return 2;
 std::vector<UINT8> raw{std::istreambuf_iterator<char>(input),{}};
 Manager manager;
 if(!manager.LoadBinaryParameters(raw.data(),raw.size())) {
  std::cerr<<manager.Error<<'\n';return 3;
 }
 std::string tag;unsigned serial=0;
 while(std::cin>>tag) {
  TuningMode branch[7]{};
  for(unsigned i=0;i<7;i++) {
   unsigned value;if(!(std::cin>>value)||value>65535)return 2;
   branch[i].mode=static_cast<ModeType>(i);branch[i].subMode.value=value;
  }
  auto *result=manager.GetModule(tag.c_str(),branch,7);
  std::cout<<serial++<<' '<<tag<<' '<<(result?result->ID:0)<<' '<<(result?result->ModeId:0)<<'\n';
 }
 return 0;
}
