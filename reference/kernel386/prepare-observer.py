from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel385/poll-boot.py').read_text().replace('k385-boot-','k386-m2m-').replace('stage=385','stage=386')
s=s.replace("path.name=='snapshot-result-private.json'","path.name=='snapshot-result-private.json' or path.name.startswith('case-') or path.name.startswith('client-private.')")
s=s.replace("worker_live=live(state['pid'],'worker.py')","client_process_live=live(state.get('client_pid',-1),'m2m-client'),worker_live=live(state['pid'],'worker.py')")
s=s.replace("report=dict(stage=386,run=run,","report=dict(stage=386,run=run,client_process_live=d['client_process_live'],")
s=s.replace("keys=['image_control_completion_passed',","keys=['ready_result','m2m_control_and_pixel_client_passed','m2m_before','m2m_after_client','m2m_final','m2m_before_removal','m2m_cleanup_retry_result','client_exit','client_live','client_report','video_node','media_node','adapter_absent','helper_absent','m2m_video_absent','image_control_completion_passed',")
s=s.replace('boot-runtime-','m2m-runtime-')
(HERE/'poll-m2m.py').write_text(s)
print('Prepared nonblocking observation of known worker/client/collector handles.')
