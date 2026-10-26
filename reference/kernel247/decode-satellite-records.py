"""Use locked MobileInsight layouts, strict v0/size/stride, including SV rows."""
from pathlib import Path
import collections,hashlib,json,math,re,struct,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel247');label=sys.argv[1];assert label in ['baseline-off','comparison-online'];src=P.parent/'kernel244/gnss-layouts';logs=json.loads((P/(label+'-decoded-log-envelopes-private.json')).read_text());rows=[];schema={}
for code,name,stem,prefix,fmt in [(0x1477,'GPS','gps','GnssGps','<BIHIffffB'),(0x1480,'GLONASS','glonass','GnssGlonass','<BIBHIffffB'),(0x1886,'GALILEO','gal','GnssGal','<BBBIHIffffB')]:
 file=src/('gnss_'+stem+'_measurement_report.h');text=file.read_text();header=re.search(r'const Fmt '+prefix+r'_Fmt \[\] = \{(.*?)\n\};',text,re.S).group(1);sv=re.search(r'const Fmt '+prefix+r'Sv_Fmt \[\] = \{(.*?)\n\};',text,re.S).group(1)
 def fields(s):
  out={};i=0
  for n,size in re.findall(r'\{\s*[A-Z_]+\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*\}',s):out[n]=(i,int(size));i+=int(size)
  return out,i
 hf,hs=fields(header);sf,ss=fields(sv);assert hs==struct.calcsize(fmt) and sf['CNo'][1]==2 and hf['NumValidReports']==(hs-1,1)
 schema[name]=dict(header_bytes=hs,sv_stride=ss,cno_offset=sf['CNo'][0],obs_state_offset=sf['ObsState'][0],measurement_status_offset=sf['MeasStat'][0],source_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
 for x in logs:
  if x['code']!=code:continue
  b=bytes.fromhex(x['payload_hex'])[16:];assert b[0]==0;n=b[hs-1];assert len(b)==hs+n*ss
  values=struct.unpack_from(fmt,b);floats=values[-5:-1];assert all(math.isfinite(v) for v in floats)
  row=dict(system=name,elapsed_ms=x['elapsed_ms'],reported_records=n,time_bias=floats[0],time_unc=floats[1],clock_freq_bias=floats[2],clock_freq_unc=floats[3],sv=[])
  if name=='GPS':row.update(gps_week=values[2],gps_msec=values[3])
  for i in range(n):
   record=b[hs+i*ss:hs+(i+1)*ss];cno=struct.unpack_from('<H',record,sf['CNo'][0])[0];obs=record[sf['ObsState'][0]];status=record[sf['MeasStat'][0]:sf['MeasStat'][0]+4]
   row['sv'].append(dict(cno_raw=cno,cno=cno/100,obs_state_raw=obs,measurement_status_hex=status.hex()))
  rows.append(row)
report=dict(stage=247,phase=label,layouts=schema,strict_version_zero_and_exact_strides=True,reported_records_not_assumed_tracking=True,clock_float_units_not_inferred=True,systems={})
for name in schema:
 rr=[x for x in rows if x['system']==name];sv=[v for x in rr for v in x['sv']];report['systems'][name]=dict(reports=len(rr),record_count_distribution=dict(collections.Counter(x['reported_records'] for x in rr)),cno_fields=len(sv),positive_cno=sum(v['cno_raw']>0 for v in sv),zero_cno=sum(v['cno_raw']==0 for v in sv),obs_state_raw_counts=dict(collections.Counter(v['obs_state_raw'] for v in sv)),measurement_status_raw_counts=dict(collections.Counter(v['measurement_status_hex'] for v in sv)),clock_ranges={k:dict(min=min(x[k] for x in rr),max=max(x[k] for x in rr)) for k in ['time_bias','time_unc','clock_freq_bias','clock_freq_unc']} if rr else {})
report['gps_week_counts']=dict(collections.Counter(x['gps_week'] for x in rows if x['system']=='GPS'))
(P/(label+'-decoded-satellites-private.json')).write_text(json.dumps(rows,indent=2)+'\n');(R/(label+'-satellite-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
