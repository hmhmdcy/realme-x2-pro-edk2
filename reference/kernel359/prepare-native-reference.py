"""Compose retained OEM instructions for the real IPA integration contract.

The unchanged mean-luminance controller target is a separate test input;
all subsequent index/table/FPS/EV/anti-banding allocation is from OEM code.
Only private output contains selected tuning values.
"""
from pathlib import Path
import json, math, struct, sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for stage in [336,346,358]:sys.path.insert(0,str(HERE.parent/f'kernel{stage}'))
from stock_lux import StockLux
from stock_active import StockActive
from stock_antibanding import StockAntibanding
library=P.parent/'kernel328/stats-source/com.qti.stats.aec.so'
lux=StockLux(library);active=StockActive(library);banding=StockAntibanding(library)
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
rows=json.loads((P/'cases-private.json').read_text());total=0
for row in rows:
    model=row['model'];m=row['match'];program=row['program']
    minLines=6 if model=='s5kgw1' else 1;maxLines=m['frame_length']-row['margin']
    lineUs=m['line_length']*1000000./m['pixel_rate']
    gain=lambda code:code/32. if model.startswith('s5k') else 1024./(1024.-code)
    minimumNs=math.floor(minLines*lineUs*1000+.5);maximumNs=math.floor(maxLines*lineUs*1000+.5)
    frameNs=math.floor(m['frame_length']*lineUs*1000+.5)
    b=program['antibanding'];blanking=b['minimum_preview_vertical_blanking_ns']
    budget=min(max(frameNs-(blanking if blanking<frameNs else 0),minimumNs),maximumNs)
    knees=[dict(gain=k['gain'],time=k['exposure_time_ns'],priority=k['priority'],index=k['index']) for k in program['knees']]
    anchor=knees[0];evPolicy=program['ev_adjustment']
    tests=[(0,0,0,500,row['minimum_code'],256),
           (1,1,10000,500,row['minimum_code'],256),
           (-1,1,8333,500,row['minimum_code'],256),
           (0,1,10000,1000,64 if model.startswith('s5k') else 512,256),
           (0,1,8333,maxLines,row['maximum_code'],0),
           (-3,0,0,minLines,row['minimum_code'],900)]
    lines=[]
    for ordinal,(ev,mode,periodUs,exposureLines,code,binIndex) in enumerate(tests):
        # First frame: no temporal smoothing. Mirror the existing controller's
        # documented saturation iteration, independently of the new allocator.
        target=min((256.5/1024)*math.exp2(ev),.95);yGain=1.
        for iteration in range(8):
            luminance=min(1.,(binIndex+.5)/1024*yGain)
            extra=min(10.,target/(luminance+.001));yGain*=extra
            if abs(extra-1)<.01:break
        currentUs=exposureLines*lineUs*gain(code)
        # utils::Duration stores double nanoseconds; retain conversion order.
        targetNs=(currentUs*1000.)*yGain
        index=lux.sensitivity((anchor['gain'],anchor['time'],anchor['index']),1.,f32(targetNs))
        selected=active.program(knees,budget,ev if evPolicy['enabled'] else 0,evPolicy['cap_gain'],evPolicy['maximum_gain'],False)
        transformed=[dict(gain=k[0],time=k[1],priority=k[2],index=k[3]) for k in selected['knees']]
        outGain,outTime,outIndex=active.lookup(transformed,index,active=True)
        period=periodUs*1000 if mode else 0
        outGain,outTime=banding.adjust(dict(enabled=int(period!=0),period=period,threshold=b['minimum_period_fraction'],min_gain=gain(row['minimum_code']),min_ns=minimumNs,max_ns=budget,blanking=blanking,method=b['fps_method']),dict(gain=outGain,time=outTime,index=outIndex))
        lines.append(' '.join(map(str,[ordinal,ev,mode,periodUs,exposureLines,code,binIndex,format(targetNs,'.17g'),format(outGain,'.9g'),outTime,format(outIndex,'.9g')])))
    row.update(minimum_lines=minLines,maximum_lines=maxLines,native_cases=len(tests),native_reference=str(P/'fixtures'/(row['name']+'.tsv')))
    Path(row['native_reference']).write_text('\n'.join(lines)+'\n');total+=len(tests)
(P/'cases-private.json').write_text(json.dumps(rows,indent=2)+'\n')
report=dict(stage=359,contexts=len(rows),composed_native_cases=total,native_index_calls=lux.calls,native_program_and_lookup_calls=active.calls,native_antibanding_calls=banding.calls,
    native_instructions=lux.instructions+active.instructions+banding.instructions,controller_first_frame_target_is_independent_test_input=True,
    stubs='index log10; table powf/log10/exp2/memcpy; logging/string; no allocator or anti-banding arithmetic stubs',passed=True)
(HERE/'native-reference-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
