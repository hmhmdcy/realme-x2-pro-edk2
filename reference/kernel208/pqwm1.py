"""Decode public SM8150 SystemStatus PQWM1 fields, retaining missing values."""
import math

FIELDS=['gps_week','gps_tow_ms','time_valid','time_source','time_unc','clock_bias','clock_bias_unc','xo_state','pga_gain','gps_bp_i','gps_bp_q','adc_i','adc_q','jammer_gps','jammer_glo','jammer_bds','jammer_gal','error_recovery','agc_gps','agc_glo','agc_bds','agc_gal','leap_seconds','leap_unc','glo_bp_i','glo_bp_q','bds_bp_i','bds_bp_q','gal_bp_i','gal_bp_q','time_unc_ns']

def sentence(text):
    text=text.strip()
    if not text.startswith('$') or '*' not in text:raise ValueError('Missing framing')
    body,check=text[1:].rsplit('*',1)
    if len(check)!=2:raise ValueError('Malformed checksum')
    total=0
    for character in body:total^=ord(character)
    if total!=int(check,16):raise ValueError('Checksum mismatch')
    return body.split(',')

def decode(text):
    fields=sentence(text)
    if fields[0]!='PQWM1' or len(fields)<=22:raise ValueError('Incomplete PQWM1')
    result={}
    for index,name in enumerate(FIELDS,1):
        value=None
        if index<len(fields) and fields[index]:
            try:
                value=float(fields[index]) if name.startswith('agc_') else int(fields[index],10)
                if not math.isfinite(value):value=None
            except ValueError:pass
        result[name]=value
    return result

def selftest():
    def wire(fields):
        body=','.join(fields);check=0
        for character in body:check^=ord(character)
        return '$'+body+'*%02X'%check
    values=['PQWM1']+[str(i) for i in range(1,32)]
    values[9]='-7';values[19]='-12.25';values[22]='';values[31]='9223372036854775807'
    result=decode(wire(values))
    assert result['pga_gain']==-7 and result['agc_gps']==-12.25
    assert result['agc_gal'] is None and result['time_unc_ns']==9223372036854775807
    assert decode(wire(values[:23]))['leap_seconds'] is None
    bad=values.copy();bad[19]='nan';assert decode(wire(bad))['agc_gps'] is None
    for text in [wire(values)[:-1]+'X',wire(values[:22]),'PQWM1,0']:
        try:decode(text)
        except ValueError:pass
        else:raise AssertionError('Invalid input accepted')
    return dict(signed_fractional_and_64bit_fields=True,missing_and_nan_not_zero=True,optional_suffix_supported=True,checksum_and_truncation_rejected=True)

if __name__=='__main__':
    import json
    print(json.dumps(selftest()))
