from pathlib import Path
import host,json
here=Path(__file__).resolve().parent;dest='/var/lib/samurai/k210-capture-tools'
host.upload(here/'capture-static-front.py',dest+'/capture-static-front-r3.py')
wrapper=(here/'pause-monitor-capture.py').read_text().replace('k210-capture-tools/capture-static-front.py','k210-capture-tools/capture-static-front-r3.py').replace('k210-static-front-capture-r2','k210-static-front-capture-r3').replace('k210-capture-monitor-fixture','k210-capture-monitor-fixture-r3')
local=host.PRIVATE/'pause-monitor-capture-r3-private.py';assert not local.exists();local.write_text(wrapper)
host.upload(local,dest+'/pause-monitor-capture-r3.py')
p=host.ssh('python3 '+dest+'/pause-monitor-capture-r3.py',timeout=120)
(host.PRIVATE/'static-capture-r3-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);assert report['six_physical_raw10_frames_captured']
q=host.ssh('cat /var/lib/samurai/k210-capture-monitor-fixture-r3/summary.json')
fixture=json.loads(q.stdout);assert fixture['monitor_resumed']
report.update(monitor_fixture=fixture,video_fd_count_excludes_paused_idle_monitor=True,first_attempt_produced_three_frames_but_exact_847MHz_assertion_stopped_validation=True,ife_clock_rounding_tolerance_hz=100)
(here/'static-front-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
