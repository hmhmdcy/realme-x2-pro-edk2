from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel330/cct-contract.cpp').read_text().replace('assert(argc==13);','assert(argc==14);')
s=s.replace('meta(7);assert(!metadata.get(controls::ColourTemperature));',
 '''meta(6);assert(metadata.get(controls::ColourTemperature)==2850);
	meta(7);assert(metadata.get(controls::ColourTemperature)==std::atoi(argv[13]));
	ipa->processStats(1,7,2,sizeof(*envelope)+sizeof(*histogram),ipa::camss::SensorContext{true,500,512,0});
	assert(!observation.status&&observation.metadata.get(controls::ColourTemperature)==std::atoi(argv[13]));''')
s=s.replace('assert(!metadata.get(controls::ColourTemperature)&&metadata.get(controls::AwbEnable).value_or(false));',
 'assert(metadata.get(controls::ColourTemperature)==std::atoi(argv[13])&&metadata.get(controls::AwbEnable).value_or(false));')
s=s.replace('CCT_CONTRACT_PASS startup/runtime packets, SOF metadata, explicit-gain clearing, auto-ignore','CCT_CONTRACT_PASS startup/runtime packets, SOF metadata, calibrated inverse for manual and auto')
(HERE/'cct-contract.cpp').write_text(s)
s=(HERE.parent/'kernel321/ipa-contract.cpp').read_text()
s=s.replace('#include <iostream>','#include <iostream>\n#include <fstream>\n#include "libipa/awb_colour_temperature.h"')
s=s.replace('assert(argc==3||argc==4);','''assert(argc==4);
	ipa::AwbIlluminantRatios points;
	std::ifstream pointFile(argv[3],std::ios::binary);
	assert(pointFile.read(reinterpret_cast<char*>(points.data()),sizeof(points)));
	ipa::AwbColourTemperatureModel model;assert(model.configure(points));
	unsigned int checkedTemperatures=0;std::optional<int32_t> firstTemperature;bool changedTemperature=false;
	auto checkCct=[&](const ControlList &metadata) {
	 auto gains=metadata.get(controls::ColourGains);assert(gains);
	 ipa::AwbColourTemperatureEstimate expected;
	 assert(model.estimate({float(1.0/(*gains)[0]),float(1.0/(*gains)[1])},&expected));
	 auto cct=metadata.get(controls::ColourTemperature);assert(cct&&*cct==std::lround(expected.kelvin));
	 if(!firstTemperature)firstTemperature=cct;
	 else if(cct!=firstTemperature)changedTemperature=true;
	 ++checkedTemperatures;
	};''')
needle='assert(observation.calls==before+1&&observation.result.status==expected);'
s=s.replace(needle,needle+'''
		if(!expected&&observation.result.parametersKnown)checkCct(observation.metadata);''')
s=s.replace('assert(recovered.get(controls::AwbEnable).value_or(false));',
 'assert(recovered.get(controls::AwbEnable).value_or(false));checkCct(recovered);')
s=s.replace('std::cout<<"AWB_CONTRACT_PASS','assert(checkedTemperatures>0&&changedTemperature);\n\tstd::cout<<"AWB_INVERSE_CONTRACT_PASS')
(HERE/'dynamic-contract.cpp').write_text(s)
print('Prepared focused inverse-CCT and synthetic AWB/SOF integration contracts.')
