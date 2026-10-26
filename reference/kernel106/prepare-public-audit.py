from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106'
s=(root/'reference/kernel105/audit-public.py').read_text().replace('kernel105','kernel106')
s=s.replace('reference/kernel104/next-session.md','reference/kernel105/next-session.md').replace('105-apr-rebind-and-first-modem-crash-smem-diagnostics.md','106-first-modem-hello-race-and-core-query-tracing.md')
s=s.replace("v['private_files_verified']==149","v['private_files_verified']==194")
s=s.replace("v['rebind_initial_timeout_preserved']","v['first_rebind_query_within_100ms_pass']")
s=s.replace('core_first_timeout_and_followup_success_preserved=True','core_first_100ms_rebind_query_pass=True,first_hello_announcement_race_preserved=True')
assert not (ref/'audit-public.py').exists();(ref/'audit-public.py').write_text(s)
print('STAGE106_PUBLIC_AUDIT_PREPARED')
