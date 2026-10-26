"""Read actual vector streams and exercise the stock CLI/SensorProxy on A.11."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,time
import dbus

os.umask(0o077)
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
out=Path(args.output);out.mkdir(mode=0o700)
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='running'
assert not subprocess.run(['pidof','iio-sensor-proxy'],capture_output=True).stdout.strip()
candidate=Path('/var/lib/samurai/k184-libssc-r2/build-r4/src/libssc.so.2')
assert hashlib.sha256(candidate.read_bytes()).hexdigest()=='45570ea41d07fd4300069b5e3ed254f5dfc0c9b660a269d293943a9834566006'
database=Path('/lib/apk/db/installed').read_bytes()
system_lib=Path('/usr/lib/libssc.so.2').read_bytes()
report={'vectors':{},'cli':{},'candidate_library_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest()}
for kind in ['accel','gyro','mag']:
    p=subprocess.run(['python3','-B','/var/lib/samurai/k187-tools/ssc-vector-probe.py',
        '--sensor',kind,'--duration','8','--output',str(out/kind)],capture_output=True,timeout=35)
    (out/(kind+'-run-private.txt')).write_bytes(p.stdout+p.stderr)
    record=json.loads((out/kind/'summary.json').read_text())
    report['vectors'][kind]=record
    assert p.returncode==0 and record['success'] and record['samples']>=100
    assert record['strictly_increasing_sensor_timestamps']
env=dict(os.environ,LD_LIBRARY_PATH=str(candidate.parent),LIBSSC_LIGHT_DATA_TYPE='wise_light',G_MESSAGES_DEBUG='all')
for kind,label in [('accelerometer','Accelerometer'),('gyroscope','Gyroscope'),('magnetometer','Magnetometer'),('compass','Compass'),('light','Light')]:
    p=subprocess.run(['ssccli','--debug','--sensor',kind,'--timeout','5'],capture_output=True,env=env,timeout=20)
    raw=(p.stdout+p.stderr).decode(errors='replace')
    (out/(kind+'-cli-private.txt')).write_bytes(p.stdout+p.stderr)
    data=dict(exit=p.returncode,samples=raw.count(label+' sensor measurement:'),disabled=(label+' sensor disabled').lower() in raw.lower())
    report['cli'][kind]=data
    assert p.returncode==0 and data['samples']>0 and data['disabled']
proxy=None;claims=[];interface=None;bus=dbus.SystemBus(private=True)
try:
    with (out/'proxy-private.txt').open('wb') as log:
        proxy=subprocess.Popen(['/usr/libexec/iio-sensor-proxy'],env=env,stdout=log,stderr=subprocess.STDOUT)
        dbus_if=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus')
        deadline=time.monotonic()+35;values={}
        while time.monotonic()<deadline:
            assert proxy.poll() is None,'SensorProxy exited early'
            if dbus_if.NameHasOwner('net.hadess.SensorProxy'):
                owner=dbus_if.GetNameOwner('net.hadess.SensorProxy')
                assert int(dbus_if.GetConnectionUnixProcessID(owner))==proxy.pid
                obj=bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy')
                properties=dbus.Interface(obj,'org.freedesktop.DBus.Properties')
                values=properties.GetAll('net.hadess.SensorProxy',timeout=5)
                if all(values.get(k) for k in ['HasAccelerometer','HasAmbientLight','HasProximity']):break
            time.sleep(.25)
        assert all(values.get(k) for k in ['HasAccelerometer','HasAmbientLight','HasProximity'])
        interface=dbus.Interface(obj,'net.hadess.SensorProxy')
        for name in ['Accelerometer','Light','Proximity']:
            getattr(interface,'Claim'+name)(timeout=5);claims.append(name)
        time.sleep(6)
        values=properties.GetAll('net.hadess.SensorProxy',timeout=5)
        report['sensor_proxy']={name:values.get(name) for name in ['HasAccelerometer','AccelerometerOrientation',
            'HasAmbientLight','LightLevel','LightLevelUnit','HasProximity','ProximityNear']}
        report['three_claims_succeeded']=True
finally:
    for name in reversed(claims):getattr(interface,'Release'+name)(timeout=5)
    bus.close()
    if proxy is not None and proxy.poll() is None:
        proxy.terminate()
        try:proxy.wait(timeout=12)
        except subprocess.TimeoutExpired:proxy.kill();proxy.wait(timeout=3)
    report['proxy_exit']=proxy.returncode if proxy is not None else None
    report['system_library_unchanged']=Path('/usr/lib/libssc.so.2').read_bytes()==system_lib
    report['package_database_unchanged']=Path('/lib/apk/db/installed').read_bytes()==database
    report['human_motion_or_orientation_validation_performed']=False
    report['absolute_compass_and_light_accuracy_verified']=False
    (out/'summary.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(report,default=str))
assert report['proxy_exit']==0 and report['system_library_unchanged'] and report['package_database_unchanged']
