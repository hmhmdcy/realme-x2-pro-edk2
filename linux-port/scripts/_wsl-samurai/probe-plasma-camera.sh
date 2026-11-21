#!/bin/sh
# The board pins libcamera to 99990.7.2 (0.7 ABI) for the camera stack.
# Verify what plasma-camera actually resolves against on the device and
# whether it is a repository package or a board copy.
set -u
echo '== libcamera / plasma-camera versions =='
apk list -I 2>/dev/null | grep -E 'libcamera|plasma-camera|samurai-camera'
echo '== who owns the plasma-camera binary and its libc deps =='
apk info -W /usr/bin/plasma-camera 2>&1
echo '== runtime link targets =='
ls -l /usr/lib/libcamera*.so* 2>/dev/null | sed 's/^/  /'
echo '== does plasma-camera link a missing soname? =='
for so in $(apk info -R plasma-camera 2>/dev/null | grep '^so:'); do
	name=${so#so:}
	if [ -e "/usr/lib/$name" ]; then
		printf '  ok      %s\n' "$name"
	else
		printf '  MISSING %s\n' "$name"
	fi
done
