from pathlib import Path
R=Path(__file__).resolve().parent
text=(R/'loc-ordered.c').read_text().replace('guint8 session = 242;','guint8 session = 244;')
marker='    if (!command(device, request, FALSE, NULL) || interrupted) goto cleanup;\n    request = request_new(client, 0x0022);'
new='''    const guint8 client_id[] = {'L','A','P','I'};
    const guint8 notify = 0;
    add_bytes(request, 16, client_id, sizeof(client_id));
    add_u32(request, 17, 1);
    add_bytes(request, 18, &notify, 1);
    if (!command(device, request, FALSE, NULL) || interrupted) goto cleanup;
    request = request_new(client, 0x0022);'''
assert text.count(marker)==1;text=text.replace(marker,new).replace('oem-before-start','afw-master-before-start')
(R/'loc-combined.c').write_text(text)
for src,dst in [('build-ordered.py','build-combined.py'),('native-ordered.py','native-combined.py'),('launch-ordered.py','launch-combined.py'),('poll-ordered.py','poll-combined.py')]:
 data=(R/src).read_text().replace('k241-oem-tools','k241-combined-tools').replace('k241-loc-ordered','k241-loc-combined')
 data=data.replace('loc-ordered.c','loc-combined.c').replace('loc-ordered','loc-combined')
 data=data.replace('native-ordered.py','native-combined.py').replace('ordered-validation.json','combined-validation.json')
 data=data.replace('ordered-build-validation.json','combined-build-validation.json')
 data=data.replace('ordered-build-host-private.log','combined-build-host-private.log').replace('ordered-launch-host-private.log','combined-launch-host-private.log').replace('ordered-poll-host-private.json','combined-poll-host-private.json')
 if dst=='launch-combined.py':data=data.replace("k241-loc-differential/state-private.json","k241-loc-afw/state-private.json")
 (R/dst).write_text(data)
print('Prepared combined AFW/master/measurement pre-start case, with explicit client identity and notification flag')
