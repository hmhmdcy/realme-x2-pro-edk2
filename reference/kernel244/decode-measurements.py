"""Decode only proven fixed header layouts; zero report count is not zero C/No."""
from pathlib import Path
import collections,importlib.util,json,math,struct
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel244');v=json.loads((P/'collect-live-packets-private.json').read_text())['private']
spec=importlib.util.spec_from_file_location('diag244decode',R/'diag_transport_boot.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
packets=[]
for line in v['diag-events-private.jsonl'].splitlines():
 x=json.loads(line)
 if x['kind']=='rx' and x.get('channel') in [1,3] and x['port']!=0xfffffffe:packets+=m.frames(bytes.fromhex(x['hex']))
decoded=[];headers=collections.defaultdict(collections.Counter)
for p in packets:
 if not p or p[0]!=0x10:continue
 assert len(p)>=16;outer,inner,code=struct.unpack_from('<HHH',p,2);assert outer==inner and inner==len(p)-4
 body=p[16:];name={0x1477:'GPS',0x1480:'GLONASS',0x1886:'GALILEO'}.get(code)
 if not name:continue
 version=body[0];row=dict(system=name,version=version,body_bytes=len(body),reported_svs=body[-1])
 if name=='GPS':
  assert len(body)>=28;version,fcount,week,msec,tbias,tunc,fbias,func,n=struct.unpack_from('<BIHIffffB',body);header_size=28
  row.update(gps_week=week,gps_msec=msec)
 elif name=='GLONASS':
  assert len(body)>=29;version,fcount,cycle,days,msec,tbias,tunc,fbias,func,n=struct.unpack_from('<BIBHIffffB',body);header_size=29
 else:
  assert len(body)>=30;version,engine,hw,fcount,week,msec,tbias,tunc,fbias,func,n=struct.unpack_from('<BBBIHIffffB',body);header_size=30;row.update(engine=engine,hardware_version=hw)
 assert n==0 and len(body)==header_size,'SV layouts require a separate stride/version validation before use'
 assert all(math.isfinite(x) for x in [tbias,tunc,fbias,func]);row.update(fcount=fcount,time_bias=tbias,time_unc=tunc,clock_freq_bias=fbias,clock_freq_unc=func,reported_svs=n);decoded.append(row);headers[name][version]+=1
report=dict(stage=244,reports=len(decoded),versions={k:dict(c) for k,c in headers.items()},sv_counts={k:dict(collections.Counter(x['reported_svs'] for x in decoded if x['system']==k)) for k in headers},
 ranges={k:{field:dict(min=min(x[field] for x in decoded if x['system']==k),max=max(x[field] for x in decoded if x['system']==k)) for field in ['time_bias','time_unc','clock_freq_bias','clock_freq_unc','fcount']} for k in headers},gps_week_counts=dict(collections.Counter(x['gps_week'] for x in decoded if x['system']=='GPS')),no_cno_fields_present=True,missing_sv_measurements_not_zero_cno=True,exact_log_lengths_validated=True,clock_float_units_not_inferred=True)
(P/'decoded-measurements-private.json').write_text(json.dumps(decoded,indent=2)+'\n');(R/'measurement-decode-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
