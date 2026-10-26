import json,host
p=host.ssh('cat /var/lib/samurai/k202r2-geoclue-first-session/progress.json && cat /var/lib/samurai/gnss-assist/watch-state.json')
(host.PRIVATE/'first-progress-private.txt').write_bytes(p.stdout)
decoder=json.JSONDecoder();progress,end=decoder.raw_decode(p.stdout.decode());watch=json.loads(p.stdout.decode()[end:])
print(json.dumps(dict(stage=202,reboot_cycle=2,nmea=progress['unique_nmea'],nonzero_distinct_gga_times=progress['ggatime_distinct'],valid_gga=progress['valid_gga'],positive_cnr_fields=progress['positive_cnr_fields'],worker_result=watch['last_result'])))
