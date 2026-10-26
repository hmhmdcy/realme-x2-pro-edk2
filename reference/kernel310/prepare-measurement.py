"""Adapt the existing SOF measurement tools for main/front; no delay assumed."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
old=HERE.parent/'kernel306'
s=(old/'delay-capture.cpp').read_text().replace('< 240','< 120')
s=s.replace('uint64_t hash =', 'std::array<uint64_t,4> lumaBands{};\n\t\t\tuint64_t hash =')
s=s.replace('if (!i) { lowest', 'if (!i && n < 320*240) lumaBands[n/(320*60)] += data[n];\n\t\t\t\t\t\tif (!i) { lowest')
s=s.replace('std::cout << "APPLICATION_FRAME', '''std::cout << "APPLICATION_LUMA request=" << request->sequence();
            for (auto sum : lumaBands) std::cout << " " << double(sum)/(320*60);
            std::cout << std::endl;
            std::cout << "APPLICATION_FRAME''')
(HERE/'delay-capture.cpp').write_text(s)
s=(old/'control-stepper.c').read_text()
s=s.replace('static const struct change changes[]={','static struct change changes[]={')
a=s.index(' {12,V4L2_CID_EXPOSURE,');b=s.index('\n};',a)
s=s[:a]+''' {12,V4L2_CID_EXPOSURE,0},{28,V4L2_CID_EXPOSURE,0},
 {44,V4L2_CID_ANALOGUE_GAIN,0},{60,V4L2_CID_ANALOGUE_GAIN,0},
 {76,V4L2_CID_EXPOSURE,0},{92,V4L2_CID_EXPOSURE,0},'''+s[b:]
a=s.index(' struct utsname identity;');b=s.index('\n char *end;',a)
s=s[:a]+''' const char *model=getenv("CAMSS_SENSOR_MODEL");
 if(!model || (strcmp(model,"s5kgw1") && strcmp(model,"imx471")))return 2;
 int lowExposure=!strcmp(model,"s5kgw1")?650:768;
 int highExposure=!strcmp(model,"s5kgw1")?1600:1800;
 int lowGain=!strcmp(model,"s5kgw1")?64:512;
 int highGain=!strcmp(model,"s5kgw1")?128:768;
 changes[0].value=changes[4].value=highExposure;
 changes[1].value=changes[5].value=lowExposure;
 changes[2].value=highGain;changes[3].value=lowGain;'''+s[b:]
s=s.replace('!strncmp(e.name,"s5k3m5 ",7)','!strncmp(e.name,model,strlen(model)) && e.name[strlen(model)]==\' \'')
s=s.replace('exposure.minimum>500||exposure.maximum<1200||gain.minimum>64||gain.maximum<128',
            'exposure.minimum>lowExposure||exposure.maximum<highExposure||gain.minimum>lowGain||gain.maximum<highGain')
s=s.replace('.value=500','.value=lowExposure').replace('.value=64','.value=lowGain')
s=s.replace('initial_exposure=500 initial_gain_code=64\\n",getpid(),s.name,v.name)',
            'initial_exposure=%d initial_gain_code=%d\\n",getpid(),s.name,v.name,lowExposure,lowGain)')
s=s.replace('x.value!=500||g.value!=64','x.value!=lowExposure||g.value!=lowGain')
s=s.replace('sof>=232','sof>=108')
(HERE/'control-stepper.c').write_text(s)
for model in ['s5kgw1','imx471']:
    profile=(HERE.parent/'kernel309'/(model+'.yaml')).read_text()
    (HERE/(model+'-measure.yaml')).write_text(profile[:profile.index('awb:')]+'...\n')
print('Prepared main/front measurement sources; no timing property added.')
