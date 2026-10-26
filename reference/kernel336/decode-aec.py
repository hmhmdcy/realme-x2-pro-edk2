"""Independently decode exposure tables and lux fields, then compare XML."""
from pathlib import Path
import json,math,struct,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;rows=[];bundles={}
def norm(x):
 if isinstance(x,float):return float(format(x,'.6g'))
 if isinstance(x,list):return [norm(v) for v in x]
 if isinstance(x,dict):return {k:norm(v) for k,v in x.items()}
 return x
priority=['AECExpIncGain','AECExpIncExpTime','AECExpIncPrioMax']
for exported in json.loads((P/'factory-aec-export-private.json').read_text()):
 name=exported['name'];index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());entries=index['entries'];raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes();base=index['base']
 def blob(uid):
  e=entries[str(uid)];return raw[base+e['offset']:base+e['offset']+e['bytes']]
 def number(data,slot):return struct.unpack_from('<f',data,slot*8)[0]
 def integer(data,slot):return struct.unpack_from('<Q',data,slot*8)[0]
 def array(data,slot):
  count,uid=integer(data,slot),integer(data,slot+1)
  if not count:return []
  block=blob(uid);assert len(block)==(count*4+7)//8*8,(name,slot,count,uid,len(block),entries[str(uid)]['name'])
  return list(struct.unpack_from('<'+str(count)+'f',block))
 def knee(uid,count):
  block=blob(uid);assert len(block)==count*32
  return [dict(gain=number(block,i*4),expTime=integer(block,i*4+1),incrementPriority=priority[integer(block,i*4+2)],expIndex=number(block,i*4+3)) for i in range(count)]
 def exposure_tables(data):
  count,uid=integer(data,5),integer(data,6);block=blob(uid);assert len(block)==count*32
  return [dict(sensitivityCorrectionFactor=number(block,i*4),expKneeEntries=knee(integer(block,i*4+2),integer(block,i*4+1)),thresAntiBandingMinExpTimePct=number(block,i*4+3)) for i in range(count)]
 decoded={'Metering':[],'Arbitration':[]}
 for root in exported['roots']:
  data=blob(root['uid']);tag=root['tag']
  if tag=='Metering':
   assert tuple(integer(data,i) for i in range(3))==(8,0,1)
   result=dict(indexCalc=dict(enableLuxIndexComp=bool(integer(data,5)),refSensitivityForExpIndexZero=number(data,6),luxIndexFilterFactor=number(data,7),bayerGridSubsmplSelect=integer(data,8)),
    lumaWeight=dict(weight=list(struct.unpack_from('<3f',data,72)),enableColorAndSensorComp=bool(integer(data,11)),refGain=list(struct.unpack_from('<3f',data,96))))
  else:
   assert len(data)==176 and tuple(integer(data,i) for i in range(3))==(1,0,0)
   result=dict(expTables=exposure_tables(data),minPreviewVertBlankTime=integer(data,7),enableEVExpTableAdj=bool(integer(data,8)),enableEVGainCapping=bool(integer(data,9)),maxEVCappingGain=number(data,10),
    ISOData=dict(previewISO100Gain=number(data,11),enableAntiBandingVsISOPrio=bool(integer(data,12)),enableISOQuantization=bool(integer(data,13)),thresQuantizationISOValue=array(data,14),quantizedISOValue=array(data,16)),
    antibandingVsFPSMethod=integer(data,18),enablePreviewManualISO=bool(integer(data,19)),enablePreviewManualExpTime=bool(integer(data,20)),enablePreviewManualFull=bool(integer(data,21)))
  decoded[tag].append(dict(uid=root['uid'],data=result))
 work=Path('/home/cy122/x2pro-linux')/('parser-k336-'+name+'-aec-r2/xml');matches=[]
 for tag,paths in exported['exported'].items():
  for relative in paths:
   xml=ET.parse(work/relative).getroot()
   if tag=='Metering':
    node=xml.find('mtrLumaCalc');calc=node.find('indexCalc');weight=node.find('lumaWeight')
    subsmpl=calc.findtext('bayerGridSubsmplSelect');subsmpl_names=['Off','SW2','SW4','Max']
    result=dict(indexCalc=dict(enableLuxIndexComp=calc.findtext('enableLuxIndexComp')=='true',refSensitivityForExpIndexZero=float(calc.findtext('refSensitivityForExpIndexZero')),luxIndexFilterFactor=float(calc.findtext('luxIndexFilterFactor')),bayerGridSubsmplSelect=subsmpl_names.index(subsmpl)),
     lumaWeight=dict(weight=[float(n.text) for n in weight.findall('weight')],enableColorAndSensorComp=weight.findtext('enableColorAndSensorComp')=='true',refGain=[float(n.text) for n in weight.findall('refGain')]))
   else:
    result=dict(expTables=[dict(sensitivityCorrectionFactor=float(t.findtext('sensitivityCorrectionFactor')),expKneeEntries=[dict(gain=float(k.findtext('gain')),expTime=int(k.findtext('expTime')),incrementPriority=k.findtext('incrementPriority'),expIndex=float(k.findtext('expIndex'))) for k in t.findall('expKneeEntries')],thresAntiBandingMinExpTimePct=float(t.findtext('thresAntiBandingMinExpTimePct'))) for t in xml.findall('expTables')],
     minPreviewVertBlankTime=int(xml.findtext('minPreviewVertBlankTime')),enableEVExpTableAdj=xml.findtext('enableEVExpTableAdj')=='true',enableEVGainCapping=xml.findtext('enableEVGainCapping')=='true',maxEVCappingGain=float(xml.findtext('maxEVCappingGain')),
     ISOData=dict(previewISO100Gain=float(xml.findtext('ISOData/previewISO100Gain')),enableAntiBandingVsISOPrio=xml.findtext('ISOData/enableAntiBandingVsISOPrio')=='true',enableISOQuantization=xml.findtext('ISOData/enableISOQuantization')=='true',
      thresQuantizationISOValue=[float(n.text) for n in xml.findall('ISOData/thresQuantizationISOValue')],quantizedISOValue=[float(n.text) for n in xml.findall('ISOData/quantizedISOValue')]),
     antibandingVsFPSMethod=['LegacyAllowFPSToDrop','StrictlyEnforceFPS','MaximizeExposureTime'].index(xml.findtext('antibandingVsFPSMethod')),enablePreviewManualISO=xml.findtext('enablePreviewManualISO')=='true',enablePreviewManualExpTime=xml.findtext('enablePreviewManualExpTime')=='true',enablePreviewManualFull=xml.findtext('enablePreviewManualFull')=='true')
   uids=[r['uid'] for r in decoded[tag] if norm(r['data'])==norm(result)];assert uids,(name,tag,relative,result)
   matches.append(dict(selector=relative,tag=tag,binary_uids=uids))
 assert {u for r in matches for u in r['binary_uids']}=={r['uid'] for r in exported['roots']}
 # These are roots equivalent for the decoded fields at the Default XML
 # selector, not a recovered mode-to-UID binding for the whole Metering root.
 default={tag:next(m for m in matches if m['tag']==tag and m['selector']=='Scenario.Default/XML/STATS/'+tag+'.xml')['binary_uids'] for tag in decoded}
 all_tables=[t for root in decoded['Arbitration'] for t in root['data']['expTables']]
 bundles[name]=dict(roots=decoded,selectors=matches,default_field_matches=default)
 rows.append(dict(name=name,metering_roots=len(decoded['Metering']),arbitration_roots=len(decoded['Arbitration']),exposure_tables=len(all_tables),exposure_knees=sum(len(t['expKneeEntries']) for t in all_tables),
  first_knee_indices=sorted({t['expKneeEntries'][0]['expIndex'] for t in all_tables}),default_field_matches=default,all_arbitration_operational_slots_match=True,all_lux_index_and_luma_weight_fields_match=True))
 print(json.dumps(rows[-1]),flush=True)
(P/'factory-aec-bundle-private.json').write_text(json.dumps(bundles,indent=2)+'\n')
(HERE/'factory-aec-validation.json').write_text(json.dumps(dict(stage=336,sources=rows,arbitration_schema='public1.0.1 minus appended disableBandingGainCapping and revision changed to1.0.0; inferred compatibility schema, not recovered OEM schema',
 original_payload_unchanged=True,physical_mode_binding_verified=False,raw_stats_to_oem_lux_luma_equivalence_verified=False,phone_changed=False,passed=True),indent=2)+'\n')
