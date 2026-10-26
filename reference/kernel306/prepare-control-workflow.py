from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel303'
for name in ['launch-capture.py','poll-capture.py','native-capture.py','analyse-joint.py','analyse-ae.py']:
 source=(OLD/name).read_text().replace('k303-','k306-').replace('stage=303','stage=306')
 source=source.replace('/var/lib/samurai/k298-work/boot-id-private.txt','/var/lib/samurai/k305-geometry-r2/boot-id-private.txt')
 if name=='native-capture.py':
  source=source.replace("str(stage/'bin/pipeline-smoke'),'imx319'","str(stage/'bin/pipeline-smoke'),'s5k3m5'")
  source=source.replace('model=imx319','model=s5k3m5')
  source=source.replace('scene_wb_is_not_factory_awb=True','unity_wb_no_awb=True')
  source=source.replace("'FIXTURE_RESULT result=0' in text","'FIXTURE_RESULT result=0' in text and 'FIXTURE_RESTORATION result=0' in text")
 if name=='analyse-joint.py':
  source=source.replace('2080 * 1000000 / 209066666','9648 * 1000000 / 481930000')
  source=source.replace('rounded(20000 / lineUs), 512','rounded(20000 / lineUs), 256')
  source=source.replace('(10000, 4.0) if r // 24 % 2 else (20000, 2.0)','(10000, 16.0) if r // 24 % 2 else (20000, 8.0)')
  source=source.replace('rounded(1024 - 1024 / g)','rounded(32 * g)')
  source=source.replace('p == 499392','p == 820560')
  source=source.replace('1024 / (1024 - g)','g / 32')
 if name=='analyse-ae.py':
  source=source.replace('2080*1000000/209066666','9648*1000000/481930000')
  source=source.replace('p==499392','p==820560').replace('4<=x<=3332 and 0<=g<=960','1<=x<=1659 and 32<=g<=512')
  source=source.replace('expectedGain=1024/(1024-g)','expectedGain=g/32')
  source=source.replace('(new[0]/(1024-new[1]))/(old[0]/(1024-old[1]))','(new[0]*new[1])/(old[0]*old[1])')
  source=source.replace('actual[e,s][0]>=3330 and actual[e,s][1]==960','actual[e,s][0]>=1657 and actual[e,s][1]==512')
  source=source.replace("print('PRIVATE_DIAGNOSTIC',e,'first_luminance',curve[0],'tail_median',median,'range',min(curve),max(curve))",
    "(host.PRIVATE/f'ae-{run}-epoch{e}-luminance-private.json').write_text(json.dumps(dict(first=curve[0],tail_median=median,minimum=min(curve),maximum=max(curve)))+'\\n')")
 compile(source,str(HERE/name),'exec');(HERE/name).write_text(source)
print('Generated current-boot telephoto control workflows; no phone action.')
