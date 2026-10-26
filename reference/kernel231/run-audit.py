from pathlib import Path
import hashlib,importlib.util,json
ref=Path(__file__).resolve().parent;p=Path('/mnt/e/edk2-samurai-out/kernel231');native=p/'native-snapshot'
sp=importlib.util.spec_from_file_location('audit',ref/'audit-file-services.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
meta=json.loads((p/'native-manifest-private.json').read_text())
for name,expected in meta['files'].items():
 data=(native/name).read_bytes();assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256']
sources=json.loads((native/'source-files-private.json').read_text())
source=sources['/run/samurai-wifi/mcfg-state/source-manifest-private.json'];assert source['exists']
manifest=json.loads((native/source['snapshot']).read_text());mdtime=manifest['modem_pr/mcfg/configs/mcfg_sw/mdtime.txt'];assert mdtime['bytes']==12
result=a.audit((native/'tftp-snapshot-private.log').read_text(),(native/'rmtfs-snapshot-private.log').read_text(),mdtime['bytes'])
assert result['rmtfs_numeric_replies']==11 and result['rmtfs_numeric_failure_replies']==0 and result['rmtfs_unparsed_reply_lines']==0 and result['rmtfs_cow_sources_loaded']==6
firm=result['known_mdtime_requests']['firmware_mdtime'];shared=result['known_mdtime_requests']['shared_mdtime']
assert firm['requests']==6 and shared['requests']==1 and result['shared_exact_wrq_requests']==0
assert all(v['local_reject_errno'] is None for v in firm['cases'])
assert all(v['opened_for_reading'] for v in firm['cases'])
assert [v['data_packet_bytes'] for v in firm['cases']]==[[],[16],[4],[],[16],[4]]
assert all(v['peer_end_of_transfer'] for v in firm['cases'] if v['rsize']==0)
assert shared['cases'][0]['local_reject_errno']==13
ota=result['known_mdtime_requests']['ota_firewall_ruleset'];work=result['known_mdtime_requests']['mcfg_workfile']
assert ota['requests']==2 and all(v['local_reject_errno']==2 for v in ota['cases']) and ota['write_attempts_with_known_path']==0
assert work['requests']==2 and work['cases'][0]['local_reject_errno']==2 and work['cases'][1]['opened_for_reading'] and work['cases'][1]['peer_end_of_transfer']
assert work['successful_write_opens']==2
assert not result['tftp_invalid_data_packet_lengths'] and not result['tftp_unmatched_rejects']
layout=json.loads((p/'stock-layout/vendor-rfs-layout-private.json').read_text());persist=json.loads((p/'stock-layout/persist-rfs-stat-only-private.json').read_text())
assert next(v for v in layout if v['path'].endswith('/mpss/shared'))['target']=='/mnt/vendor/persist/rfs/shared'
assert next(v for v in persist if v['path'].endswith('/rfs/shared/configs/mcfg_sw/mdtime.txt'))['missing']
stock_work=json.loads((ref/'stock-work-layout-validation.json').read_text())
assert not next(v for v in stock_work['metadata'] if v['relative'].endswith('/ota_firewall/ruleset'))['exists']
assert not next(v for v in stock_work['metadata'] if v['relative'].endswith('/mcfg.tmp'))['exists']
# Source-derived wire behavior is separate from captured packet evidence.
server=Path('/mnt/e/edk2-samurai-out/kernel207/tftp-clean-rebuild-r2/tqftpserv/tqftpserv.c').read_text()
assert hashlib.sha256(server.encode()).hexdigest()=='5bdb6ef75af723cad63aac1511cdcaae6bfc8113749383bebea13d50b2b5103a'
fragment=server[server.index('fd = translate_open(filename, O_RDONLY);'):];fragment=fragment[:fragment.index('\n\tif (tsize')]
assert 'TFTP_ERROR_ENOENT' in fragment and 'TFTP_ERROR_EACCESS' not in fragment
result.update(stage=231,current_boot230_only_not226_session_timeline=True,stock_shared_is_persist_namespace=True,stock_shared_mdtime_missing=True,firmware_and_shared_not_aliases=True,
              rrq_wire_error1_inferred_from_exact_running_source=True,not_a_captured_wire_packet=True,shared_cow_or_error_mapping_not_deployed=True,no_new_gnss_session_or_nv_change=True,zero_cnr_root_cause_not_established=True)
result.update(stock_ota_firewall_ruleset_also_absent=True,stock_mcfg_tmp_absent=True,mcfg_tmp_created_in_runtime_but_valid_contents_not_proven=True,all_four_rejected_opens_classified_without_inventing_files=True)
(ref/'file-service-audit-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
