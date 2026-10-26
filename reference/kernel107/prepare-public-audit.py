from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel107';old=root/'reference/kernel106'
s=(old/'audit-public.py').read_text().replace('kernel106','kernel107')
s=s.replace('reference/kernel105/next-session.md','reference/kernel106/next-session.md').replace('106-first-modem-hello-race-and-core-query-tracing.md','107-qrtr-hello-reply-and-automatic-wifi-start.md')
s=s.replace("v['private_files_verified']==194","v['private_files_verified']==154")
s=s.replace("v['apr_rebind_dispatch_restored']","v['first_hello_service_announcements_pass']").replace("v['first_rebind_query_within_100ms_pass']","v['native_api_query_pass']")
s=s.replace("v['fatal_mpss']==1 and not v['first_automatic_wifi_start_pass'] and v['manual_mpss_recovery_count']==1","v['fatal_mpss']==0 and v['first_automatic_wifi_start_pass'] and v['manual_mpss_recovery_count']==0")
s=s.replace('first_automatic_failure_and_single_recovery_preserved=True','automatic_start_without_manual_recovery_verified=True').replace('core_first_100ms_rebind_query_pass=True','native_api_query_pass=True').replace('first_hello_announcement_race_preserved=True','first_hello_response_and_announcements_pass=True')
assert not (ref/'audit-public.py').exists();(ref/'audit-public.py').write_text(s)
s=(old/'validate-host.ps1').read_text().replace('kernel106','kernel107').replace('k106','k107');assert not (ref/'validate-host.ps1').exists();(ref/'validate-host.ps1').write_text(s)
print('STAGE107_PUBLIC_AND_HOST_AUDITS_PREPARED')
