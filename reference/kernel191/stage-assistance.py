import host
p=host.ssh('python3 -',input=b"from pathlib import Path\np=Path('/var/lib/samurai/k191-assistance');p.mkdir(mode=0o700)\nprint('New assistance directory created')\n");print(p.stdout.decode())
host.upload(host.PRIVATE/'assistance/xtra-private.bin','/var/lib/samurai/k191-assistance/xtra-private.bin');print('TLS global assistance file staged')
