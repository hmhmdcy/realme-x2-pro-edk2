import host
p=host.ssh("cat /var/lib/samurai/k221-loc-readonly/compile-private.log",timeout=25)
(host.PRIVATE/'loc-compile-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode())
