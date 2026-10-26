"""Conservative UTC injection bound from chronyc tracking, in milliseconds."""
import math

def uncertainty(tracking,query_age_seconds=0.0,transport_margin_ms=250):
    fields={line.split(':',1)[0].strip():line.split(':',1)[1].strip() for line in tracking.splitlines() if ':' in line}
    if fields.get('Leap status')!='Normal':raise ValueError('Clock not synchronised')
    stratum=int(fields['Stratum'])
    if not 1<=stratum<=15:raise ValueError('Invalid reference stratum')
    reference=fields['Reference ID'].split()[0].upper()
    if reference=='7F7F0101':raise ValueError('Local reference is not an external UTC source')
    values={name:float(fields[name].split()[0]) for name in ['System time','Root delay','Root dispersion','Skew']}
    if not all(math.isfinite(value) for value in values.values()):raise ValueError('Nonfinite clock error')
    if values['Root dispersion']<0 or values['Skew']<0:raise ValueError('Negative error bound')
    if not math.isfinite(query_age_seconds) or not 0<=query_age_seconds<=30:raise ValueError('Stale clock sample')
    if not math.isfinite(transport_margin_ms) or transport_margin_ms<100:raise ValueError('Insufficient transport margin')
    bound=abs(values['System time'])+values['Root dispersion']+max(0,values['Root delay'])/2
    bound+=query_age_seconds*values['Skew']/1_000_000
    result=math.ceil(bound*1000+transport_margin_ms)
    if not 1<=result<=0xffffffff:raise ValueError('Time uncertainty outside wire range')
    return dict(uncertainty_ms=result,chrony_error_bound_ms=bound*1000,transport_margin_ms=transport_margin_ms,stratum=stratum)

def selftest():
    sample='Reference ID : CB007101\nStratum : 3\nSystem time : 0.012 seconds slow of NTP time\nRoot delay : 0.274 seconds\nRoot dispersion : 0.028 seconds\nSkew : 25 ppm\nLeap status : Normal\n'
    assert uncertainty(sample)['uncertainty_ms']==427
    assert uncertainty(sample.replace('0.012','-0.012'))['uncertainty_ms']==427
    assert uncertainty(sample,query_age_seconds=30)['uncertainty_ms']==428
    for text in [sample.replace('Normal','Not synchronised'),sample.replace('0.028','nan'),sample.replace('0.028','-0.1'),sample.replace('Stratum : 3','Stratum : 16'),sample.replace('CB007101','7F7F0101')]:
        try:uncertainty(text)
        except ValueError:pass
        else:raise AssertionError('Invalid clock accepted')
    try:uncertainty(sample,query_age_seconds=31)
    except ValueError:pass
    else:raise AssertionError('Stale clock accepted')
    return dict(milliseconds_ceiled_with_margin=True,slow_and_fast_offsets_bounded=True,age_and_frequency_error_included=True,unsynchronised_local_nonfinite_negative_and_stale_rejected=True)

if __name__=='__main__':
    import json
    print(json.dumps(selftest()))
