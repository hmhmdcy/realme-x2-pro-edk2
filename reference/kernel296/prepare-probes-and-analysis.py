"""Require correct startup counters and compile probes before any phone execution."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel295'
for name,condition in [('samurai-stats.c','(frame==0||frame==72||frame==90)&&sum!=820560'),('samurai-optical.c','sum!=499392')]:
 p=ROOT/name;s=p.read_text();needle=' if(frame%9==8){' if name=='samurai-stats.c' else ' if(frame%6==5){'
 assert needle in s
 s=s.replace(needle,' if('+condition+'){fprintf(stderr,"STATS_POPULATION_FAILURE frame=%u sum=%" PRIu64 "\\n",frame,sum);errno=EPROTO;return -1;}\n'+needle,1)
 p.write_text(s)
# Compilation uses the existing strict ABI/header/runtime guards.
s=(ROOT.parent/'kernel294/prepare-tools.py').read_text().split("s=(OLD/'native-wb-params.py')")[0]
s=s.replace('/kernel294','/kernel296').replace('stage=294','stage=296').replace('wrong-kernel-k294','wrong-kernel-k296')
exec(compile(s,'compile-probes.py','exec'),{'__file__':__file__})
s=(OLD/'analyze-statistics.py').read_text().replace('k295','k296').replace('stage=295','stage=296').replace('kernel_build=295','kernel_build=296')
s=s.replace("print(json.dumps({k:v for k,v in report.items() if k!='phases'},indent=2));assert report['steady_roi_contracts_passed']", "print(json.dumps({k:v for k,v in report.items() if k!='phases'},indent=2));assert report['passed']")
(ROOT/'analyze-statistics.py').write_text(s);compile(s,'analyze-statistics.py','exec')
s=(OLD/'analyze-optical-statistics.py').read_text().replace('k295','k296').replace('stage=295','stage=296').replace('kernel_build=295','kernel_build=296')
s=s.replace('statistics_initialization_or_first_valid_frame_fix_required=True','statistics_initialization_or_first_valid_frame_fix_required=bool(invalid)')
s=s.replace('initial_packet_delivered_without_error_flag=True','initial_packet_delivered_without_error_flag=bool(invalid)')
s=s.replace("print(json.dumps(report,indent=2));assert response and invalid and invalid[0]['frame']==0", "print(json.dumps(report,indent=2));assert response and not invalid")
# Visual review must be recorded only after actually viewing the new frame.
a=s.index('review=dict(');b=s.index('print(json.dumps(report',a);s=s[:a]+s[b:]
(ROOT/'analyze-optical-statistics.py').write_text(s);compile(s,'analyze-optical-statistics.py','exec')
s=(OLD/'archive-entrypoints.py').read_text() if (OLD/'archive-entrypoints.py').exists() else (ROOT.parent/'kernel293/archive-entrypoints.py').read_text()
s=s.replace('camera-before292-2026-10-19','camera-before296-2026-10-19').replace('stage=292','stage=296').replace('prior_documented_stage=291','prior_documented_stage=295')
exec(compile(s,'archive-entrypoints.py','exec'),{'__file__':str(ROOT/'archive-entrypoints.py')})
print('Startup counters now hard requirements in the physical probes; prior entrypoints archived.')
