from pathlib import Path
import hashlib,json,subprocess
base=Path('/var/lib/samurai/k115-services')
assert Path('/proc/sys/kernel/random/boot_id').read_text()==Path('/var/lib/samurai/k114-final-health/boot-id-private.txt').read_text()
base.mkdir(mode=0o700,exist_ok=True)
before_pid=Path('/run/elogind.pid').read_text().strip()
assert before_pid.isdecimal()
assert Path(f'/proc/{before_pid}/exe').resolve()==Path('/usr/libexec/elogind/elogind')
elogind=Path('/etc/init.d/elogind')
original=(base/'elogind-before').read_text() if (base/'elogind-before').exists() else elogind.read_text()
assert original.count('supervisor=supervise-daemon')==1
assert original.count('$supervisor $RC_SVCNAME --signal HUP')==1
swap=Path('/etc/init.d/postmarketos-zram-swap')
swap_original=(base/'zram-before').read_text() if (base/'zram-before').exists() else swap.read_text()
assert swap_original.count('\tprovide swap\n')==1
base.joinpath('elogind-before').write_text(original)
base.joinpath('zram-before').write_text(swap_original)
updated=original.replace('supervisor=supervise-daemon','''# Track the daemon PID written by elogind, including D-Bus activation.
supervisor=
command_args="--daemon"
pidfile=/run/elogind.pid
retry="TERM/5/KILL/2"''').replace('$supervisor $RC_SVCNAME --signal HUP','start-stop-daemon --signal HUP --exec "$command" --pidfile "$pidfile"')
updated += '''
# D-Bus may have activated elogind before OpenRC reaches this service.
start() {
    if [ -r "$pidfile" ]; then
        local daemon_pid="$(cat "$pidfile")"
        case "$daemon_pid" in ''|*[!0-9]*) daemon_pid=invalid;; esac
        if [ "$daemon_pid" != invalid ] && kill -0 "$daemon_pid" 2>/dev/null &&
           [ "$(readlink "/proc/$daemon_pid/exe")" = "$command" ]; then
            ebegin "Tracking existing ${name}"
            service_set_value command "$command"
            service_set_value pidfile "$pidfile"
            eend 0
            return 0
        fi
    fi
    ssd_start
}
'''
elogind.write_text(updated)
swap.write_text(swap_original.replace('\tprovide swap\n','\t# OpenRC already ships a real swap service; do not shadow it.\n'))
for p in [elogind,swap]:
    subprocess.run(['sh','-n',str(p)],check=True)
subprocess.run(['rc-service','elogind','zap'],check=True,stdout=base.joinpath('elogind-zap.txt').open('w'),stderr=subprocess.STDOUT)
subprocess.run(['rc-service','elogind','start'],check=True,stdout=base.joinpath('elogind-start.txt').open('w'),stderr=subprocess.STDOUT)
subprocess.run(['rc-service','elogind','status'],check=True,stdout=base.joinpath('elogind-status.txt').open('w'),stderr=subprocess.STDOUT)
assert Path('/run/elogind.pid').read_text().strip()==before_pid
assert len(subprocess.check_output(['pgrep','-x','elogind-daemon']).splitlines())==1
assert not Path('/run/openrc/failed/elogind').exists()
subprocess.run(['rc-service','elogind','reload'],check=True,stdout=base.joinpath('elogind-reload.txt').open('w'),stderr=subprocess.STDOUT)
subprocess.run(['busctl','--system','introspect','org.freedesktop.login1','/org/freedesktop/login1','org.freedesktop.login1.Manager'],check=True,stdout=base.joinpath('login1-interface-private.txt').open('w'),stderr=subprocess.STDOUT)
result=subprocess.run(['rc-status','default'],capture_output=True,text=True,check=True)
base.joinpath('rc-status.txt').write_text(result.stdout)
base.joinpath('rc-status-errors.txt').write_text(result.stderr)
assert 'real and virtual service' not in result.stderr
subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],check=True,stdout=base.joinpath('nv-check.txt').open('w'),stderr=subprocess.STDOUT)
report=dict(elogind_openrc_started=True,existing_daemon_adopted_without_restart=True,login1_dbus_interface_pass=True,reload_pass=True,swap_service_collision_removed=True,zram_runtime_unavailable_on_kernel113=True,sensors_not_fixed=True,goal_complete=False)
base.joinpath('validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
