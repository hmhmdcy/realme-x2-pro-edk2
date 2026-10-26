from pathlib import Path
import json
R=Path(__file__).parent
def summarize(runs,modes,system):
 rows=[];checks=0;photos=0
 for run in runs:
  d=json.loads((R/('camera-'+str(run)+'-validation.json')).read_text());o=json.loads((R/('ownership-'+str(run)+'-validation.json')).read_text());p=d['probe_result']
  assert d['diagnostic_completed'] and o['held_changes']==0 and o['held_without_extra_loan']==0 and o['missing_busy']==0 and o['not_recycled_errors']==0
  assert p['shared_bufferpool'] and p['application_copy_env'] is None and p['held_pts_changed']==0
  assert (p['source_plugin']=='/usr/lib/gstreamer-1.0/libgstpipewire.so')==system
  checks+=p['held_checked'];photos+=len(p['shots']);rows.append(dict(kind='photo',id=run,checks=p['held_checked'],photos=len(p['shots'])))
 for mode in modes:
  d=json.loads((R/('compat-'+str(mode)+'-validation.json')).read_text());p=d['probe_result'];assert d['diagnostic_completed'] and p['candidate_library_overrides']!=system
  for c in p['clients']:assert c['exit_code']==0 and c['held_content_changed']==0 and c['not_recycled_errors']==0 and c['pts_strictly_increasing']
  n=sum(c['held_checked'] for c in p['clients']);checks+=n;rows.append(dict(kind='clients',id=mode,checks=n))
 return dict(rows=rows,held_prefix_bytes_checked_per_frame=65536,total_checks=checks,content_changes=0,pts_changes=0,recycle_errors=0,photos_saved=photos)
candidate=summarize([12,13,14],[6000141,6000142,6000143],False);production=summarize([16,17],[6000151,6000152,6000153,6000154],True)
gui=json.loads((R/'snapshot-gui-validation.json').read_text());flow=json.loads((R/'snapshot-flow-validation.json').read_text());image=json.loads((R/'snapshot-photo-0-validation.json').read_text());health=json.loads((R/'final-health-validation.json').read_text())
assert gui['diagnostic_completed'] and gui['app_exit_code']==0 and image['decoded'] and flow['recycle_errors']==0 and health['common_fix_deployed']
report=dict(stage=265,version='1.6.9-r3',candidate=candidate,production=production,production_saved_photos_including_gui=production['photos_saved']+len(gui['gui_control']['new_jpegs']),actual_snapshot_new_buffers=flow['new_buffers'],actual_snapshot_render_calls=flow['sink_render_calls'],actual_snapshot_pts_span_seconds=flow['source_pts_span_seconds'],actual_gui_front_jpeg_decoded=True,gui_camera_switch_not_yet_validated=True,production_uses_system_paths_without_copy_or_candidate_overrides=True,all_production_tests_used_final_daemons=health['production_pipewire_and_wireplumber_identities'],full_abuild_not_executed=True,complete_camera_adaptation=False)
(R/'production-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(candidate_checks=candidate['total_checks'],production_checks=production['total_checks'],production_saved_photos=report['production_saved_photos_including_gui'],content_changes=0),indent=2))

