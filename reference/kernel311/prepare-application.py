"""Build a state-driven runtime WB request probe from the measured310 app."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel310/camera-smoke.cpp').read_text()
a=s.index('static void setRequestControls');b=s.index('\nclass Capture',a)
s=s[:a]+'''static unsigned int changePending=0;
static void setRequestControls(Request *request, unsigned int sequence, unsigned int epoch)
{
 request->controls().clear();
 if (!changePending) return;
 if (changePending==1) {
  request->controls().set(controls::AwbEnable,false);
  request->controls().set(controls::ColourGains,{1.25f,.75f});
 } else if (changePending==2) request->controls().set(controls::ColourGains,{2.f,.5f});
 else {
  request->controls().set(controls::AwbEnable,true);
  request->controls().set(controls::ColourGains,{7.f,7.f}); // Ignored while AWB is enabled.
 }
 std::cout << "APPLICATION_CONTROL epoch=" << epoch << " request=" << sequence << " phase=" << changePending << std::endl;
 changePending=0;
}
'''+s[b:]
s=s.replace('bool finished() const { return frames >= 120 || (lockedRun >= 8 && (!automaticAe || stableSensorRun >= 8)); }',
            'unsigned int phase=0, observedRun=0;\n    bool finished() const { return frames>=180 || phase==4; }')
s=s.replace('!request->metadata().get(controls::AwbEnable).value_or(false)',
            '!request->metadata().get(controls::AwbEnable).has_value()')
needle='\t\t\tlockedRun = locked ? lockedRun + 1 : 0;'
replacement=needle+'''
            const bool enabled=request->metadata().get(controls::AwbEnable).value_or(false);
            const bool manual=phase==1 || phase==2;
            const float wantedRed=phase==1 ? 1.25f:2.f, wantedBlue=phase==1 ? .75f:.5f;
            bool matched=manual ? (!enabled && gains && std::abs((*gains)[0]-wantedRed)<.0001f && std::abs((*gains)[1]-wantedBlue)<.0001f) : (enabled && locked);
            observedRun=matched ? observedRun+1:0;
            if (observedRun>=8) {
                ++phase;observedRun=0;
                if (phase<4) changePending=phase;
                std::cout << "APPLICATION_PHASE epoch=" << epoch << " phase=" << phase << " after_request=" << request->sequence() << std::endl;
            }
            if (!enabled && locked) ++failed;
            std::cout << "APPLICATION_AWB_MODE epoch=" << epoch << " request=" << request->sequence() << " enabled=" << enabled << std::endl;'''
if s.count(needle)!=1:raise RuntimeError('Application changed')
s=s.replace(needle,replacement)
s=s.replace('++frames;\n\t\tif (!finished())', '++frames;\n        if (frames>=180 && phase!=4) ++failed;\n\t\tif (!finished())')
s=s.replace('capture.nextRequest = 4; capture.epoch = epoch;',
            'capture.nextRequest = 4; capture.epoch = epoch; capture.phase=capture.observedRun=changePending=0;')
(HERE/'camera-smoke.cpp').write_text(s)
print('Prepared state-driven auto/manual/manual-only/auto runtime requests.')
