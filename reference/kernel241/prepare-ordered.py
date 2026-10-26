from pathlib import Path
R=Path(__file__).resolve().parent
text=(R.parent/'kernel226/loc-session.c').read_text()
text=text.replace('strcmp(argv[1], "high")))','strcmp(argv[1], "high") && strcmp(argv[1], "oem")))')
text=text.replace('high = !strcmp(argv[1], "high");','high = !strcmp(argv[1], "high") || !strcmp(argv[1], "oem");')
text=text.replace('guint8 session = 226;','guint8 session = 242;')
marker='    if (interrupted || ambiguous_query) goto cleanup;\n    if (probe)'
extra='''    QmiMessage *protocol_query = request_new(client, 0x0055);
    guint64 protocol_mask = GUINT64_TO_LE(0x60c); /* SUPL/LPP/LPPe UP+CP */
    add_bytes(protocol_query, 1, (const guint8 *)&protocol_mask, 8);
    (void)command(device, protocol_query, TRUE, NULL);
    (void)command(device, request_new(client, 0x00a9), TRUE, NULL);
    if (interrupted || ambiguous_query) goto cleanup;
    if (probe)'''
assert text.count(marker)==1;text=text.replace(marker,extra)
marker='    QmiMessage *request = request_new(client, 0x0021);'
extra='''    QmiMessage *request = request_new(client, 0x00ba);
    add_u32(request, 1, 0xbaabcdef);
    if (!command(device, request, TRUE, NULL) || interrupted) goto cleanup;
    request = request_new(client, 0x0088);
    guint64 report_mask = GUINT64_TO_LE(0x3f), no_poly = 0;
    add_bytes(request, 16, (const guint8 *)&report_mask, 8);
    add_bytes(request, 17, (const guint8 *)&no_poly, 8);
    if (!command(device, request, TRUE, NULL) || interrupted) goto cleanup;
    request = request_new(client, 0x00d0);
    add_u32(request, 1, 2);
    gboolean resume_supported = command(device, request, TRUE, NULL);
    printf("{\\"kind\\":\\"resume_result\\",\\"applied\\":%s}\\n", resume_supported ? "true" : "false");
    if (interrupted || ambiguous_query) goto cleanup;
    request = request_new(client, 0x0021);'''
assert text.count(marker)==1;text=text.replace(marker,extra)
text=text.replace('GUINT64_TO_LE(0x187)','GUINT64_TO_LE(0x01000187)')
old='''    printf("{\\"kind\\":\\"observation_begin\\",\\"seconds\\":90,\\"session_id\\":226,\\"accuracy_high\\":%s}\\n", high ? "true" : "false");'''
new='''    printf("{\\"kind\\":\\"phase\\",\\"name\\":\\"oem-before-start\\",\\"applied\\":true,\\"elapsed_us\\":%" G_GINT64_FORMAT "}\\n", g_get_monotonic_time()-began);'''
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace('    success = !interrupted;','''    request = request_new(client, 0x0088);
    add_bytes(request, 16, (const guint8 *)&no_poly, 8);
    add_bytes(request, 17, (const guint8 *)&no_poly, 8);
    gboolean report_cleared = command(device, request, TRUE, NULL);
    printf("{\\"kind\\":\\"report_cleanup\\",\\"cleared\\":%s}\\n", report_cleared ? "true" : "false");
    success = !interrupted && !ambiguous_query;''')
(R/'loc-ordered.c').write_text(text)
for src,dst in [('build-probe.py','build-ordered.py'),('native-differential.py','native-ordered.py'),('launch-differential.py','launch-ordered.py'),('poll-differential.py','poll-ordered.py')]:
 data=(R/src).read_text().replace('k241-loc-tools','k241-oem-tools').replace('k241-loc-differential','k241-loc-ordered')
 data=data.replace('loc-differential.c','loc-ordered.c').replace('loc-differential','loc-ordered')
 data=data.replace('native-differential.py','native-ordered.py').replace('differential-validation.json','ordered-validation.json')
 data=data.replace('probe-build-validation.json','ordered-build-validation.json')
 data=data.replace('build-host-private.log','ordered-build-host-private.log').replace('launch-host-private.log','ordered-launch-host-private.log').replace('poll-host-private.json','ordered-poll-host-private.json')
 data=data.replace('observation_seconds=360','observation_seconds=90').replace('maximum_observation_seconds=360','maximum_observation_seconds=90')
 data=data.replace("[str(binary),'high']","[str(binary),'oem']").replace('len(phases)==4','len(phases)==1')
 data=data.replace('33,34,35,50,51,63,75,136,186,208','33,34,35,50,51,63,75,85,136,169,186,208')
 if dst=='launch-ordered.py':
  data=data.replace("p=r/'k241-oem-tools';assert not", "assert json.loads((r/'k241-loc-differential/state-private.json').read_text())['terminal']\np=r/'k241-oem-tools';assert not")
 (R/dst).write_text(data)
print('Prepared fresh-CID pre-start comparison and read-only protocol/capability queries; not dispatched')
