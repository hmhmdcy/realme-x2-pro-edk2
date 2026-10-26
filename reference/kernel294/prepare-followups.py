"""Preserve prior entrypoints and prepare private analysis/regression helpers."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[1];OLD=ROOT.parent/'kernel293'
s=(OLD/'archive-entrypoints.py').read_text().replace('camera-before292-2026-10-19','camera-before294-2026-10-19').replace('stage=292','stage=294').replace('prior_documented_stage=291','prior_documented_stage=293')
exec(compile(s,'archive-entrypoints.py','exec'),{'__file__':str(ROOT/'archive-entrypoints.py')})
s=(OLD/'analyze-wb-params.py').read_text().replace('kernel293','kernel294').replace('k293','k294').replace('stage=293','stage=294').replace('kernel_build=293','kernel_build=294').replace('wb-params','stats').replace('range(8,81,9)','range(8,99,9)')
s=s.replace("'image_reopen_defaults']","'image_reopen_defaults','stats_stopped','stats_late_restart']").replace('np.ones((9,3))','np.ones((11,3))')
(ROOT/'analyze-stats-color.py').write_text(s);compile(s,'analyze-stats-color.py','exec')
s=(OLD/'inspect-layering.py').read_text().replace('k293-work','k294-work').replace('stage=293','stage=294').replace('reference/kernel293/layering','reference/kernel294/layering')
(ROOT/'inspect-layering.py').write_text(s);compile(s,'inspect-layering.py','exec')
s=(OLD/'final-health.py').read_text().replace('k293-work','k294-work').replace("'#293 '","'#294 '").replace('stage=293','stage=294').replace('kernel_build=293','kernel_build=294').replace('k293-deployment/module-inventory','k294-deployment/module-inventory').replace('k293-services-verified','k294-services-verified').replace('k293-tools/final-health','k294-tools/final-health')
needle="assert len(prior292_inventory)==778 and prior292_inventory=={str(p.relative_to(prior292)):sha(p) for p in prior292.rglob('*.ko')}"
assert needle in s
s=s.replace(needle,needle+"\nprior293=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k293+')\nprior293_inventory=json.loads((r/'k293-deployment/module-inventory-private.json').read_text())\nassert len(prior293_inventory)==778 and prior293_inventory=={str(p.relative_to(prior293)):sha(p) for p in prior293.rglob('*.ko')}\n")
# Handle either real default SSC success or its known attach failure explicitly.
start=s.index("assert ssc['attempted'] and not ssc['started']")
end=s.index("\ndb=Path('/lib/apk/db/installed')",start)
s=s[:start]+'''assert ssc['attempted']
ssc_ok=bool(ssc['started'])
if ssc_ok:
 assert subprocess.run(['rc-service','iio-sensor-proxy','status'],capture_output=True).returncode==0
 bus=dbus.SystemBus(private=True);prop=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties')
 proxy={k:bool(prop.Get('net.hadess.SensorProxy',k)) for k in ['HasAccelerometer','HasAmbientLight','HasProximity']};bus.close()
 assert all(proxy.values())
else:
 assert ssc['stopped'] and ssc['readiness_failure']['daemon_returncode']==4
 assert subprocess.run(['rc-service','iio-sensor-proxy','status'],capture_output=True).returncode!=0
 proxy={k:False for k in ['HasAccelerometer','HasAmbientLight','HasProximity']}
 restore=json.loads((r/'k294-desktop-restore-r1/summary.json').read_text());assert restore['desktop_started'] and restore['dependency_config_unchanged'] and restore['failed_slpi_start_not_retried']
assert sha('/etc/conf.d/greetd')=='290ac45da696238afa1341d65d82bd28898fef749cdc77ff2b2bc19647211323'
dsps={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*')}
assert all(dsps[n]=='running' for n in ['modem','adsp']) and dsps['slpi']==('running' if ssc_ok else 'offline')
''' +s[end:]
s=s.replace('whole_system_healthy=False,ssc_default_start_failed=True,ssc_failure_exit=4,desktop_recovered_with_temporary_nodeps=True,automatic_rotation_available=False','whole_system_healthy=ssc_ok,ssc_default_start_failed=not ssc_ok,ssc_failure_exit=None if ssc_ok else 4,desktop_recovered_with_temporary_nodeps=not ssc_ok,automatic_rotation_available=ssc_ok')
s=s.replace('standard_wb_params_verified=True','standard_wb_params_verified=True,standard_bhist_validation_pending=True,old293_778_modules_preserved=True')
(ROOT/'final-health.py').write_text(s);compile(s,'final-health.py','exec')
for name in ['inspect-ssc-failure.py','inspect-readiness.py','restore-desktop.py']:
 s=(OLD/name).read_text().replace('k293','k294').replace('stage=293','stage=294').replace('kernel_build=293','kernel_build=294')
 (ROOT/name).write_text(s);compile(s,name,'exec')
print('Archived nine actual-k293 entrypoints and prepared analysis/health helpers.')
