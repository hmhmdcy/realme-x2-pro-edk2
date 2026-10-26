"""Decode only non-identifying GNSS measurement quality from LOC 0x86.

Fixed Qualcomm IDL: qmiLocSVMeasurementStructT has 90 wire bytes, not C padding.
"""
import collections,struct

def decode_array(raw):
    if not raw or raw[0]>80 or len(raw)!=1+90*raw[0]:
        raise ValueError('Invalid fixed LOC measurement array length')
    result=dict(entries=raw[0],positive_cno=0,zero_cno=0,track=0,search=0,
                fresh_valid=0,fresh_true=0,dont_use=0,maximum_cno_dbhz=None)
    for i in range(raw[0]):
        start=1+90*i
        status=struct.unpack_from('<I',raw,start+3)[0]
        valid,measurement=struct.unpack_from('<QQ',raw,start+11)
        cno=struct.unpack_from('<H',raw,start+27)[0]
        result['positive_cno']+=int(cno>0);result['zero_cno']+=int(cno==0)
        result['track']+=int(status==3);result['search']+=int(status==2)
        result['fresh_valid']+=int(bool(valid&0x08000000))
        result['fresh_true']+=int(bool(valid&measurement&0x08000000))
        result['dont_use']+=int(bool(valid&measurement&0xffc0000000000000))
        result['maximum_cno_dbhz']=max(result['maximum_cno_dbhz'] or 0,cno/10)
    return result

def summarize_measurements(records):
    count=collections.Counter();lengths=collections.Counter();errors=[];maximum=None
    for row in records:
        if row['kind']!='indication' or row['message_id']!=0x86:continue
        count['events']+=1
        raw=bytes.fromhex(row['tlvs'].get('27',''))
        if not raw:count['array_missing']+=1;continue
        lengths[len(raw)]+=1
        try:result=decode_array(raw)
        except ValueError as error:errors.append(str(error));continue
        count['arrays']+=1
        if result['entries']==0:count['empty_arrays']+=1
        for key,value in result.items():
            if key!='maximum_cno_dbhz':count[key]+=value
        if result['maximum_cno_dbhz'] is not None:maximum=max(maximum or 0,result['maximum_cno_dbhz'])
    return dict(counts=dict(count),array_lengths=dict(lengths),maximum_cno_dbhz=maximum,errors=errors)

def regression():
    raw=bytearray(91);raw[0]=1
    struct.pack_into('<I',raw,4,3);struct.pack_into('<QQ',raw,12,0x08000000,0x08000000)
    struct.pack_into('<H',raw,28,427)
    result=decode_array(raw)
    assert result['positive_cno']==1 and result['maximum_cno_dbhz']==42.7 and result['track']==1 and result['fresh_true']==1
    assert decode_array(b'\0')['entries']==0
    rejected=0
    for bad in [b'',b'\x01',bytes(raw[:-1]),bytes(raw)+b'\0',b'\x51'+bytes(90*81)]:
        try:decode_array(bad)
        except ValueError:rejected+=1
    assert rejected==5
    return dict(positive_packet_passed=True,empty_not_zero_measurements=True,malformed_packets_rejected=rejected)
