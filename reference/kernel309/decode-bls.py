"""Reuse the established BLS12 typed-vector decoder for main/front references."""
from pathlib import Path
import json,math,struct
import host
HERE=Path(__file__).resolve().parent
reports=[]
for path in host.PRIVATE.glob('com.qti.tuned.*.bin'):
    raw=path.read_bytes()
    table,count=struct.unpack_from('<II',raw,0x98)
    sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
    _,so,ss=sections[0];_,base,size=sections[1]
    assert ss%72==0 and base+size<=len(raw)
    symbols=[]
    for pos in range(so,so+ss,72):
        uid=struct.unpack_from('<Q',raw,pos)[0]
        name=raw[pos+8:pos+40].split(b'\0')[0].decode()
        offset,length=struct.unpack_from('<QQ',raw,pos+56)
        assert offset<=size and length<=size-offset
        symbols.append({'uid':uid,'name':name,'offset':offset,'size':length})
    byid={r['uid']:r for r in symbols}
    def vector(uid,name,n,width):
        r=byid[uid]
        assert 0<n<=10000 and r['name']==name and r['size']==n*width*8
        return [struct.unpack_from('<'+'Q'*width,raw,base+r['offset']+i*width*8) for i in range(n)]
    def f(value):
        assert not value>>32
        value=struct.unpack('<f',struct.pack('<I',value))[0]
        assert math.isfinite(value)
        return value
    roots=[]
    for r in symbols:
        if r['name']!='bls12_ife':continue
        w=vector(r['uid'],r['name'],1,17)[0]
        assert w[1:4]==(1,2,0) and w[0] in [0,1]
        leaves=[]
        for drc in vector(w[16],'mod_bls12_drc_gain_data',w[15],4):
            for hdr in vector(drc[3],'mod_bls12_hdr_aec_data',drc[2],8):
                for led in vector(hdr[7],'mod_bls12_led_idx_data',hdr[6],3):
                    for aec in vector(led[2],'mod_bls12_aec_data',led[1],6):
                        for cct in vector(aec[5],'mod_bls12_cct_data',aec[4],7):
                            values=[f(v) for v in cct[2:]]
                            assert all(0<=v<=16383 for v in values)
                            leaves.append(values)
        roots.append({'uid':r['uid'],'enabled':w[0],'leaves':leaves})
    assert roots
    (host.PRIVATE/(path.stem+'-bls.json')).write_text(json.dumps({'roots':roots},indent=2)+'\n')
    reports.append({'source':path.name,'ife_roots':len(roots),'ife_regions':sum(len(r['leaves']) for r in roots),
                    'all_enabled':all(r['enabled'] for r in roots),
                    'unique_offset_r_gr_gb_b':sorted({tuple(l) for r in roots for l in r['leaves']})})
report={'stage':309,'typed_BLS12_schema_reused_from306':True,'independent_parser_not_repeated':True,
        'individual_module_binding_not_confirmed':True,'files':reports}
(HERE/'factory-bls-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
