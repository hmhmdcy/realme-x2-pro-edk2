"""Report the observed SSC failure explicitly; do not relabel it a healthy system."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;p=ROOT/'final-health.py';s=p.read_text();start=s.index('bus=dbus.SystemBus(private=True)');end=s.index("db=Path('/lib/apk/db/installed')",start)
s=s[:start]+'''
ssc=json.loads(Path('/run/samurai-ssc/state.json').read_text())
assert ssc['attempted'] and not ssc['started'] and ssc['stopped'] and ssc['readiness_failure']['daemon_returncode']==4
assert subprocess.run(['rc-service','iio-sensor-proxy','status'],capture_output=True).returncode!=0
proxy={k:False for k in ['HasAccelerometer','HasAmbientLight','HasProximity']}
restore=json.loads((r/'k293-desktop-restore-r1/summary.json').read_text());assert restore['desktop_started'] and restore['dependency_config_unchanged'] and restore['failed_slpi_start_not_retried']
assert sha('/etc/conf.d/greetd')=='290ac45da696238afa1341d65d82bd28898fef749cdc77ff2b2bc19647211323'
dsps={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*')}
assert all(dsps[n]=='running' for n in ['modem','adsp']) and dsps['slpi']=='offline'

'''+s[end:]
needle=' experimental_tpg_nv12_transport_verified=True,';assert needle in s
s=s.replace(needle,''' whole_system_healthy=False,ssc_default_start_failed=True,ssc_failure_exit=4,desktop_recovered_with_temporary_nodeps=True,automatic_rotation_available=False,
 camera_tests_and_resource_health_passed=True,
'''+needle)
compile(s,str(p),'exec');p.write_text(s)
print('Final report now preserves failed default SSC startup and temporary desktop recovery.')
