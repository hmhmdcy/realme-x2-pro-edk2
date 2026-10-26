from pathlib import Path
ref=Path(__file__).resolve().parent
s=(ref/'prepare-live-native.py').read_text().replace('k197-live-prepare-r6','k197-live-prepare-r3');(ref/'prepare-fixed-live-native.py').write_text(s)
s=(ref/'capture-front-session.py').read_text().replace('k197-front-capture-r2','k197-front-capture-r3').replace('k197-live-prepare-r6','k197-live-prepare-r3')
s=s.replace('camss_refreshed=False','camss_refreshed=False;camss_candidate_loaded=False;camss_original_removed=False;original_camss=None')
s=s.replace(' rebind(False);camss_refreshed=True;rebind(True)', ''' rebind(False);camss_refreshed=True
 original_camss=Path(subprocess.check_output(['modinfo','-n','qcom-camss'],text=True).strip());report['original_camss_sha256']=hashlib.sha256(original_camss.read_bytes()).hexdigest();save()
 candidate=json.loads((stage/'camss-module-build-validation.json').read_text());assert hashlib.sha256((stage/'qcom-camss.ko').read_bytes()).hexdigest()==candidate['module_sha256']
 assert command(['rmmod','qcom_camss']).returncode==0;camss_original_removed=True
 assert command(['insmod',str(stage/'qcom-camss.ko')]).returncode==0;camss_candidate_loaded=True
 assert (camss/'driver').exists();report['camss_candidate_loaded']=True;save()''')
s=s.replace(" if Path('/sys/module/imx471').exists():", " if camss_candidate_loaded:\n  assert command(['rmmod','qcom_camss']).returncode==0;camss_candidate_loaded=False\n if Path('/sys/module/imx471').exists():",1)
s=s.replace(" if camss_refreshed:rebind(True);topology('original-restored');report['camss_original_graph_restored']=True;save()", " if camss_original_removed:\n  assert hashlib.sha256(original_camss.read_bytes()).hexdigest()==report['original_camss_sha256']\n  assert command(['modprobe','qcom-camss']).returncode==0;assert (camss/'driver').exists();report['camss_original_module_restored']=True\n elif camss_refreshed:rebind(True)\n if camss_refreshed:topology('original-restored');report['camss_original_graph_restored']=True;save()")
(ref/'capture-front-fixed-session.py').write_text(s);print('Prepared capture with temporary CAMSS module and original-module restoration')
