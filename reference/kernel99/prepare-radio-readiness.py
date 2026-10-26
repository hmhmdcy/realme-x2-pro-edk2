from pathlib import Path
import difflib

root=Path('/mnt/e/RealmeX2Pro edk2/reference')
source=(root/'kernel97/samurai-wifi').read_text()
old='''    for attempt in $(seq 1 60); do
        if [ -e /sys/class/remoteproc/remoteproc0/state ] &&
           resolve modem 524288 > /dev/null 2>&1; then break; fi
        sleep 1
    done
    prepare'''
new='''    sources_ready=0
    for attempt in $(seq 1 60); do
        if [ -e /sys/class/remoteproc/remoteproc0/state ] && all_sources_ready; then
            sources_ready=1
            break
        fi
        echo "WIFI_WAIT_SOURCES attempt=$attempt uptime=$(cut -d ' ' -f1 /proc/uptime)"
        sleep 1
    done
    [ "$sources_ready" = 1 ] || { echo WIFI_SOURCE_WAIT_TIMEOUT >&2; return 1; }
    prepare'''
assert source.count(old)==1
helper='''all_sources_ready()
{
    for spec in modem:524288 modemst1:4096 modemst2:4096 fsg:4096 fsc:256 oppostanvbk:20480 oppodycnvbk:20480; do
        resolve "${spec%%:*}" "${spec#*:}" > /dev/null 2>&1 || return 1
    done
}
'''
after=source.replace('prepare()\n{',helper+'prepare()\n{').replace(old,new)
target=root/'kernel99/samurai-wifi'
assert not target.exists()
target.write_text(after)
(root/'kernel99/wifi-all-source-readiness.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),after.splitlines(True),fromfile='a/usr/sbin/samurai-wifi',tofile='b/usr/sbin/samurai-wifi')))
print('RADIO_READINESS_RAM_CANDIDATE_PREPARED_NOT_EMBEDDED')
