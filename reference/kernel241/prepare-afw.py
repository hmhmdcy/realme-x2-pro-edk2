from pathlib import Path
R=Path(__file__).resolve().parent
text=(R.parent/'kernel226/loc-session.c').read_text().replace('guint8 session = 226;','guint8 session = 243;')
marker='    if (!command(device, request, FALSE, NULL) || interrupted) goto cleanup;\n    request = request_new(client, 0x0022);'
replacement='''    add_u32(request, 17, 1); /* explicit AFW client, as in the actual vendor library */
    if (!command(device, request, FALSE, NULL) || interrupted) goto cleanup;
    request = request_new(client, 0x0022);'''
assert text.count(marker)==1;text=text.replace(marker,replacement)
old='''    printf("{\\"kind\\":\\"observation_begin\\",\\"seconds\\":90,\\"session_id\\":226,\\"accuracy_high\\":%s}\\n", high ? "true" : "false");'''
new='''    printf("{\\"kind\\":\\"phase\\",\\"name\\":\\"afw-only\\",\\"applied\\":true,\\"elapsed_us\\":%" G_GINT64_FORMAT "}\\n", g_get_monotonic_time()-began);'''
assert text.count(old)==1;text=text.replace(old,new)
(R/'loc-afw.c').write_text(text)
for src,dst in [('build-probe.py','build-afw.py'),('native-differential.py','native-afw.py'),('launch-differential.py','launch-afw.py'),('poll-differential.py','poll-afw.py')]:
 data=(R/src).read_text().replace('k241-loc-tools','k241-afw-tools').replace('k241-loc-differential','k241-loc-afw')
 data=data.replace('loc-differential.c','loc-afw.c').replace('loc-differential','loc-afw')
 data=data.replace('native-differential.py','native-afw.py').replace('differential-validation.json','afw-validation.json')
 data=data.replace('probe-build-validation.json','afw-build-validation.json')
 data=data.replace('build-host-private.log','afw-build-host-private.log').replace('launch-host-private.log','afw-launch-host-private.log').replace('poll-host-private.json','afw-poll-host-private.json')
 data=data.replace('observation_seconds=360','observation_seconds=90').replace('maximum_observation_seconds=360','maximum_observation_seconds=90')
 data=data.replace('len(phases)==4','len(phases)==1')
 data=data.replace('33,34,35,50,51,63,75,136,186,208','33,34,35,50,51,63,75')
 if dst=='launch-afw.py':
  data=data.replace("p=r/'k241-afw-tools';assert not", "assert json.loads((r/'k241-loc-ordered/state-private.json').read_text())['terminal']\np=r/'k241-afw-tools';assert not")
 (R/dst).write_text(data)
print('Prepared AFW-only single-variable 90s case; no master, report configuration or platform notification')
