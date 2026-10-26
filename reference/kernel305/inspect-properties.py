import host
q=host.ssh('cam -c 4 -p',timeout=20)
print(q.stdout.decode())
