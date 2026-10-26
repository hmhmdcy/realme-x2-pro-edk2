from pathlib import Path
import collections,json,re
ns={};exec((Path(__file__).parent/'verify-tests.py').read_text().split("names=['audio-runtime'",1)[0],ns)
band=ns['archive']('24g-once');net=ns['archive']('auto-network')
before=net['wpa.log'];after=band['wpa.log'];assert after.startswith(before)
log=after[len(before):].decode()
v=dict(verified_24g_archive=True,short_attempt_pass=band['result.txt']==b'SINGLE_24G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\n',new_connected_events=log.count('CTRL-EVENT-CONNECTED'),key_negotiation_completions=log.count('WPA: Key negotiation completed'),wrong_key_events=log.count('WRONG_KEY'),disconnect_reasons=dict(collections.Counter(re.findall(r'CTRL-EVENT-DISCONNECTED[^\n]* reason=(\d+)',log))),association_frequencies=dict(collections.Counter(re.findall(r'Trying to associate[^\n]*freq=(\d+)',log))),last_state=re.search(rb'^wpa_state=(.+)$',band['status-after.txt'],re.M)[1].decode(),mpss_state=band['state.txt'].decode().splitlines()[-1])
v['test_files']=[n for n in ['dhcp.txt','route.txt','gateway.txt','dns.txt','http.txt'] if n in band]
dhcp=band.get('dhcp.txt',b'').decode()
v['dhcp_discover_count']=dhcp.count('sending discover');v['dhcp_no_lease']=bool(re.search(r'no lease|lease fail',dhcp,re.I));v['dhcp_lease_obtained']=bool(re.search(r'lease of .* obtained',dhcp))
v['new_reason7_count']=log.count(' reason=7 ')
v['http_bytes']=len(band.get('http.txt',b''));v['http_example_received']=b'Example Domain' in band.get('http.txt',b'')
v['gateway_statistics']=[l for l in band.get('gateway.txt',b'').decode().splitlines() if 'packet' in l]
v['http_log']=band.get('http.log',b'').decode()
(ns['out']/'24g-failure-analysis.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v,indent=2))
