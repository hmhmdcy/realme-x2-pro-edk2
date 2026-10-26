import host
q=host.raw_ssh('cat /sys/kernel/debug/dynamic_debug/control | head -1; tail -80 /var/lib/samurai/k314-dual-r3/dmesg-after.txt',check=False)
print(q.stdout.decode())
