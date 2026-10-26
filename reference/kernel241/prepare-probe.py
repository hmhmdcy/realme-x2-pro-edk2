"""Derive a bounded differential probe from the already validated raw LOC client."""
from pathlib import Path
import ast,json
R=Path(__file__).resolve().parent
text=(R.parent/'kernel226/loc-session.c').read_text()
text=text.replace('/* Bounded same-CID LOC observation. Only GET, REGISTER, START and STOP. No NV. */',
'''/* Same-CID incremental comparison: baseline, master, platform resume, measurement.
 * Transient LOC client/notification/reporting only. No lock/constellation NV SET.
 * Does not change DMS power state, persistent files, firmware or hardware rails. */''')
text=text.replace('guint8 session = 226;', 'guint8 session = 241;')
old='''    printf("{\\"kind\\":\\"observation_begin\\",\\"seconds\\":90,\\"session_id\\":226,\\"accuracy_high\\":%s}\\n", high ? "true" : "false");
    pump(90);
    success = !interrupted;'''
new=r'''    printf("{\"kind\":\"phase\",\"name\":\"baseline\",\"elapsed_us\":%" G_GINT64_FORMAT "}\n", g_get_monotonic_time()-began);
    pump(90);
    if (interrupted) goto cleanup;
    request = request_new(client, 0x00ba);
    add_u32(request, 1, 0xbaabcdef);
    gboolean master = command(device, request, TRUE, NULL);
    printf("{\"kind\":\"phase\",\"name\":\"master\",\"applied\":%s,\"elapsed_us\":%" G_GINT64_FORMAT "}\n", master ? "true" : "false", g_get_monotonic_time()-began);
    if (interrupted || ambiguous_query) goto cleanup;
    pump(90);
    if (interrupted) goto cleanup;
    request = request_new(client, 0x00d0);
    add_u32(request, 1, 2); /* actual vendor RESUME, not DMS power */
    gboolean resume = command(device, request, TRUE, NULL);
    printf("{\"kind\":\"phase\",\"name\":\"master-resume\",\"applied\":%s,\"elapsed_us\":%" G_GINT64_FORMAT "}\n", resume ? "true" : "false", g_get_monotonic_time()-began);
    if (interrupted || ambiguous_query) goto cleanup;
    pump(90);
    if (interrupted) goto cleanup;
    request = request_new(client, 0x0088);
    guint64 report_mask = GUINT64_TO_LE(0x3f), no_poly = 0;
    add_bytes(request, 16, (const guint8 *)&report_mask, 8);
    add_bytes(request, 17, (const guint8 *)&no_poly, 8);
    gboolean measurement = command(device, request, TRUE, NULL);
    if (interrupted || ambiguous_query) goto cleanup;
    if (measurement) {
        request = request_new(client, 0x0021);
        mask = GUINT64_TO_LE(0x01000187);
        add_bytes(request, 1, (const guint8 *)&mask, 8);
        measurement = command(device, request, FALSE, NULL);
    }
    printf("{\"kind\":\"phase\",\"name\":\"master-resume-measurement\",\"applied\":%s,\"elapsed_us\":%" G_GINT64_FORMAT "}\n", measurement ? "true" : "false", g_get_monotonic_time()-began);
    if (interrupted || ambiguous_query) goto cleanup;
    pump(90);
    if (interrupted) goto cleanup;
    request = request_new(client, 0x0088);
    add_bytes(request, 16, (const guint8 *)&no_poly, 8);
    add_bytes(request, 17, (const guint8 *)&no_poly, 8);
    gboolean report_cleared = command(device, request, TRUE, NULL);
    printf("{\"kind\":\"report_cleanup\",\"cleared\":%s}\n", report_cleared ? "true" : "false");
    success = !interrupted && !ambiguous_query;'''
assert text.count(old)==1
text=text.replace(old,new)
assert text.count('pump(90);')==4
(R/'loc-differential.c').write_text(text)
print('Prepared four incremental 90s phases; exact vendor IDs 0xba/0xd0/0x88, explicit reporting cleanup')
