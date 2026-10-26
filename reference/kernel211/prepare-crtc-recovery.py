from pathlib import Path
import ast
here=Path(__file__).resolve().parent
text=(here/'disable-crtc.py').read_text().replace("read_text().strip() == '0'","read_text().strip() == '512'",1)
text=text.replace("assert log.count('Oops:') == 0 and log.count('WARNING:') == 0","assert log.count('Oops:') == 0 and log.count('WARNING:') == 2\nassert log.count(\"cam_cc_mclk2_clk status stuck at 'off'\") == 2\nassert all('clk-branch.c:87 at clk_branch_toggle' in line for line in log.splitlines() if 'WARNING:' in line)")
ast.parse(text);(here/'disable-crtc-after-warning.py').write_text(text)
text=(here/'continue-quiesce-after-warning.sh').read_text();start=text.index('python3 /tmp/k211-disable-crtc.py')
tail=text[start:].replace('/tmp/k211-disable-crtc.py','/tmp/k211-disable-crtc-after-warning.py')
prefix='''#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k211-before-reboot
dest=/var/lib/samurai/k211-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 512
test ! -e "$dest/quiesce-validation.json"
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test ! -e "$dest/explicit-crtc-first-failure-private.txt"
cp "$dest/explicit-crtc-disable.txt" "$dest/explicit-crtc-first-failure-private.txt"
'''
(here/'finish-quiesce-crtc-after-warning.sh').write_text(prefix+tail)
print('CRTC recovery accepts only the two captured MCLK warnings; resumes after completed radio/DSP shutdown.')
