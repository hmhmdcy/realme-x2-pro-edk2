from pathlib import Path
import sys
ref=Path(__file__).resolve().parent
sys.path.insert(0,str(ref.parent/'kernel284'));import storage
source=storage.mounted_build().parent/'source354'
t=(source/'include/trace/events/power.h').read_text()
for name in ['device_pm_callback_start','device_pm_callback_end']:
    start=t.index('TRACE_EVENT('+name)
    end=t.index('\n);',start)+3
    print(t[start:end])
