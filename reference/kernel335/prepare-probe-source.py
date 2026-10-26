from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel332/cct-smoke.cpp').read_text()
s=s.replace(' std::vector<int> targets;',''' std::vector<int> targets;
 std::vector<std::array<float,9>> expected;
 const std::array<float,9> manual{0,0,1,0,.75f,0,1,0,0};''')
s=s.replace('  const bool applied=target>0 ? temperature==target && awb==false : temperature.has_value() && awb==true && locked==true;', '''  auto matrix=request->metadata().get(controls::ColourCorrectionMatrix);
  bool matrixMatches=false;
  if(matrix && temperature && *temperature>=1500 && *temperature<=12000) {
   const auto &wanted=target==-2?manual:expected[*temperature-1500];
   matrixMatches=!std::memcmp(matrix->data(),wanted.data(),36);
  }
  const bool manualGain=gains && std::abs((*gains)[0]-1.25f)<.01f && std::abs((*gains)[1]-.75f)<.01f;
  const bool applied=matrixMatches && (target>0 ? temperature==target && awb==false : target==-1 ? temperature.has_value() && awb==true && locked==true : awb==false && (target!=-3 || manualGain));''')
s=s.replace('std::cout<<"CCT_FRAME sequence="','std::cout<<"CCM_FRAME phase="<<phase<<" sequence="')
s=s.replace('   std::cout<<std::endl;','''   std::cout<<" matrix-match="<<matrixMatches;
   if(matrix){std::cout<<" matrix=";for(unsigned i=0;i<9;i++)std::cout<<(i?",":"")<<(*matrix)[i];}
   std::cout<<std::endl;''',1)
s=s.replace('   if(next)request->controls().set(controls::AwbEnable,true);','''   if(next) {
    const int wanted=targets[phase];
    request->controls().set(controls::AwbEnable,wanted==-1);
    if(wanted>0)request->controls().set(controls::ColourTemperature,wanted);
    else if(wanted==-2)request->controls().set(controls::ColourCorrectionMatrix,Span<const float,9>(manual));
    else if(wanted==-3)request->controls().set(controls::ColourGains,{1.25f,.75f});
   }''')
s=s.replace(' int expected=0;std::ifstream expectedFile(argv[7]);if(!(expectedFile>>expected)||expected<1500||expected>12000)return 2;', ' std::ifstream expectedFile(argv[7],std::ios::binary);if(!expectedFile)return 2;')
s=s.replace('Capture capture;capture.targets=std::vector<int>{expected,-1};','''Capture capture;capture.targets=std::vector<int>{6500,2850,-2,6500,-3,-1};
 for(int kelvin=1500;kelvin<=12000;kelvin++) {
  std::array<char,40> packet;std::array<float,9> matrix;
  if(!expectedFile.read(packet.data(),40) || !expectedFile.read(reinterpret_cast<char*>(matrix.data()),36))return 2;
  capture.expected.push_back(matrix);
 }
''')
s=s.replace(' if(!supported)return 5;',' if(!supported || camera->controls().find(&controls::ColourCorrectionMatrix)==camera->controls().end())return 5;')
s=s.replace(' {const std::array<float,2> gains{1.25f,.75f};initial.set(controls::ColourGains,Span<const float,2>(gains));}',' initial.set(controls::ColourTemperature,6500);')
s=s.replace('"-"+std::to_string(capture.targets[i])+"-private.nv12"','"-phase"+std::to_string(i)+"-private.nv12"')
s=s.replace('"CCT_RESULT frames="','"CCM_RESULT frames="')
(HERE/'ccm-smoke.cpp').write_text(s)
print('Prepared six-phase TPG probe with independent matrix expectations.')
