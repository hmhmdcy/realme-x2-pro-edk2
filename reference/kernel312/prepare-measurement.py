"""Reuse measured control probes and select new modes through sensorConfig."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel310'
s=(OLD/'delay-capture.cpp').read_text()
s=s.replace('config->at(0).size = Size(320, 240);','''const char *size=std::getenv("CAMSS_SENSOR_SIZE");
    if (size) {
        unsigned int width=0,height=0;
        if (std::sscanf(size,"%ux%u",&width,&height)!=2) return 6;
        SensorConfiguration sensor; sensor.bitDepth=10;sensor.outputSize=Size(width,height);
        config->sensorConfig=sensor;
    }
    config->at(0).size = Size(320, 240);''')
s=s.replace('#include <chrono>','#include <chrono>\n#include <cstdlib>\n#include <cstdio>')
(HERE/'delay-capture.cpp').write_text(s)
s=(OLD/'control-stepper.c').read_text()
s=s.replace('int lowExposure=!strcmp(model,"s5kgw1")?650:768;',
            'int lowExposure=!strcmp(model,"s5kgw1")?650:350;')
s=s.replace('int highExposure=!strcmp(model,"s5kgw1")?1600:1800;',
            'int highExposure=!strcmp(model,"s5kgw1")?1600:900;')
(HERE/'control-stepper.c').write_text(s)
s=(OLD/'build-measurement.py').read_text().replace('310','312')
(HERE/'build-measurement.py').write_text(s)
print('Prepared standard sensorConfig probes for the two added modes.')
