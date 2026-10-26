"""Public libcamera AF trigger/cancel probe: no application-side search or lens writes."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');name='af-native278-r2'
shutil.copyfile(R/'af-probe-build-validation.json',R/'af-probe-build-r1-validation.json')
s=(R.parent/'kernel277/focus-metadata277.cpp').read_text()
s=s.replace('static bool automaticMode = false;','static bool automaticMode = false;\nstatic std::string scenario = "scan";\nstatic bool finishing = false;')
s='\n'.join(x for x in s.splitlines() if not x.startswith('static const std::array<std::pair<int, float>, 8> controlPlan'))+'\n'
start=s.index('    static void manual(');end=s.index('    int queue(',start)
s=s[:start]+'''    static void manual(ControlList &controls, unsigned int index = 0)
    {
        controls.set(controls::AeEnable, false);
        controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
        controls.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
        controls.set(controls::ExposureTime, 32000);
        controls.set(controls::AnalogueGain, 1.0f);
        controls.set(controls::AfMode, controls::AfModeAuto);
        if (scenario != "idle" && (index == 8 || (scenario == "retrigger" && index == 60)))
            controls.set(controls::AfTrigger, controls::AfTriggerStart);
        if (scenario == "scan" && (index == 20 || index == 24))
            controls.set(controls::AfTrigger, controls::AfTriggerStart);
        if (scenario == "scan" && finishing)
            controls.set(controls::AfTrigger, controls::AfTriggerCancel);
        if ((scenario == "cancel" || scenario == "retrigger") && index == 24)
            controls.set(controls::AfTrigger, controls::AfTriggerCancel);
    }
'''+s[end:]
start=s.index('        if (!automaticMode && index % 12 >= 6) {');end=s.index('        ReadMapping rawMap',start)
s=s[:start]+'''        if (index >= 12)
            require(std::abs(*exposure - 32000) <= 40 && std::abs(*gain - 1) < .03f,
                    "fixed AF test exposure/gain");
        auto afState = request->metadata().get(controls::AfState);
        auto afMode = request->metadata().get(controls::AfMode);
        require(afState && afMode && *afMode == controls::AfModeAuto, "standard AF state/mode metadata");
        if (scenario == "idle" || index < 8 || ((scenario == "cancel" || scenario == "retrigger") && index >= 24 && index < 60))
            require(*afState == controls::AfStateIdle, "no scan before trigger or after cancel");
'''+s[end:]
old="        out << '}';\n"
assert s.count(old)==1;s=s.replace(old,'''        out << ",\\\"queued_af_trigger\\\":";
        if (auto value=request->controls().get(controls::AfTrigger)) out << *value;
        else out << "null";
        out << ",\\\"af_state\\\":" << *afState << ",\\\"af_mode\\\":" << *afMode << '}';
        if ((scenario == "scan" || (scenario == "retrigger" && index >= 60)) &&
            (*afState == controls::AfStateFocused || *afState == controls::AfStateFailed)) {
            std::scoped_lock lock(queueMutex_,mutex_);
            if (!finishing) { requestedFrames = std::min(requestedFrames,index+13); finishing = true; }
        }''')
s=s.replace('std::chrono::seconds(100)','std::chrono::seconds(180)')
s=s.replace('if (argc != 9 ||','if (argc != 10 ||')
old='    requestedFrames = automaticMode ? 180 : 24;'
assert s.count(old)==1;s=s.replace(old,'''    scenario = argv[9];
    if (scenario != "idle" && scenario != "scan" && scenario != "cancel" && scenario != "retrigger" && scenario != "stop") return 2;
    requestedFrames = scenario == "idle" ? 48 : scenario == "cancel" ? 72 : scenario == "stop" ? 36 : 900;''')
anchor='int main(int argc, char **argv)\n{'
assert s.count(anchor)==1;s=s.replace(anchor,anchor+'''
    if (argc == 2 && std::string(argv[1]) == "--support") {
        CameraManager manager; if (manager.start()) return 1;
        auto camera=manager.get("/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10");
        if (!camera) return 2;
        std::cout << "{\\\"af_mode\\\":" << (camera->controls().count(&controls::AfMode)?"true":"false")
                  << ",\\\"af_trigger\\\":" << (camera->controls().count(&controls::AfTrigger)?"true":"false")
                  << ",\\\"af_state\\\":" << (camera->controls().count(&controls::AfState)?"true":"false") << "}\\n";
        camera.reset(); manager.stop(); return 0;
    }
''')
(R/(name+'.cpp')).write_text(s)
source=SDK/'private'/(name+'.cpp');assert not source.exists();source.write_text(s.replace('#include "focus_stats.h"','#include "focus278-stats-r2.h"'))
header=SDK/'private/focus278-stats-r2.h';assert not header.exists();header.write_bytes((R.parent/'kernel277/focus_stats.h').read_bytes())
prefix='/candidate277-r23'
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+prefix+'/usr/include/libcamera','/private/'+source.name,'-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib','-lcamera','-lcamera-base','-o','/private/'+name],capture_output=True,timeout=240)
(host.PRIVATE/'af-probe-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
target=host.PRIVATE/name;shutil.copyfile(SDK/'private'/name,target)
d=dict(stage=278,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((R/(name+'.cpp')).read_bytes()).hexdigest(),
 cpp20_werror_clean=True,public_libcamera_af_controls_only=True,no_application_search=True,no_raw_i2c_or_lens_ioctl=True,manual_distance_not_claimed=True)
(R/'af-probe-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
