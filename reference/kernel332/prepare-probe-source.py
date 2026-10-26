from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel330/cct-smoke.cpp').read_text()
s=s.replace('#include <iostream>','#include <iostream>\n#include <fstream>\n#include <iomanip>')
s=s.replace('const bool applied=target ? temperature==target : !temperature;',
 '''auto awb=request->metadata().get(controls::AwbEnable);
  auto locked=request->metadata().get(controls::AwbLocked);
  const bool applied=target>0 ? temperature==target && awb==false : temperature.has_value() && awb==true && locked==true;''')
s=s.replace('<<" settled="<<settled;', '<<" settled="<<settled<<" awb="<<awb.value_or(false)<<" locked="<<locked.value_or(false);')
s=s.replace('if(next)request->controls().set(controls::ColourTemperature,targets[phase]);',
 'if(next)request->controls().set(controls::AwbEnable,true);')
s=s.replace('int useCct=std::atoi(argv[7]);if(useCct!=0 && useCct!=1)return 2;',
 'int expected=0;std::ifstream expectedFile(argv[7]);if(!(expectedFile>>expected)||expected<1500||expected>12000)return 2;\n std::cout<<std::setprecision(9);')
s=s.replace('capture.targets=useCct?std::vector<int>{6500,2850}:std::vector<int>{0};','capture.targets=std::vector<int>{expected,-1};')
s=s.replace('if(supported!=bool(useCct))return 5;','if(!supported)return 5;')
s=s.replace('if(useCct)initial.set(controls::ColourTemperature,6500);\n else {const std::array<float,2> gains{1,1};initial.set(controls::ColourGains,Span<const float,2>(gains));}',
 '{const std::array<float,2> gains{1.25f,.75f};initial.set(controls::ColourGains,Span<const float,2>(gains));}')
(HERE/'cct-smoke.cpp').write_text(s)
print('Prepared manual-gain to automatic-AWB internal-pattern CCT probe.')
