from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel430/runtime.py').read_text().replace('k430-dc-topology-','k434-gtm-')
exec(compile(source,str(HERE/'runtime.py'),'exec'))
if action=='observe' and d['state'].get('terminal') and not d['state'].get('passed'):
 p=HERE/('runtime-'+attempt+'-validation.json');public=json.loads(p.read_text());public['state']['failure']='Capture acceptance failed; original traceback and logs retained privately.';public['state']['failure_details_private']=True;p.write_text(json.dumps(public,indent=2)+'\n')
