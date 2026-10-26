"""Probe standard sensorConfig and default 3A without per-camera startup overrides."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel310/camera-smoke.cpp').read_text()
s=s.replace('#include <chrono>','#include <chrono>\n#include <cstdio>')
s=s.replace('config->at(0).size = Size(320, 240);','''const char *size=std::getenv("CAMSS_SENSOR_SIZE");
    if (size) {
        unsigned int width=0,height=0;
        if (std::sscanf(size,"%ux%u",&width,&height)!=2) return 6;
        SensorConfiguration sensor;sensor.bitDepth=10;sensor.outputSize=Size(width,height);
        config->sensorConfig=sensor;
    }
    config->at(0).size = Size(320, 240);''')
a=s.index('\t\tControlList controls(camera->controls());');b=s.index('\n\t\t{\n\t\t\tstd::lock_guard',a)
s=s[:a]+s[b:]
s=s.replace('camera->start(&controls)','camera->start()')
(HERE/'camera-smoke.cpp').write_text(s)
s=(HERE.parent/'kernel310/build-joint.py').read_text().replace('310','312')
(HERE/'build-application.py').write_text(s)
print('Prepared sensorConfig selection with camera.start() default controls.')
