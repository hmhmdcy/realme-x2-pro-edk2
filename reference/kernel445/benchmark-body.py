 state['focus_benchmarks']={}
 fixtures=json.loads((root/'focus-fixtures-private.json').read_text());assert len(fixtures)==4
 for fixture in fixtures:
  path=Path(fixture['phone_path']);assert str(path).startswith('/var/lib/samurai/k442-callback-timing-r9/')
  assert hashlib.sha256(path.read_bytes()).hexdigest()==fixture['sha256']
  label=fixture['label'];logpath=root/('focus-bench-'+label+'.log')
  with logpath.open('xb') as output:
   child=subprocess.Popen([str(root/'focus-bench'),str(path),str(fixture['width']),str(fixture['height']),str(fixture['stride']),'16',str(fixture['score'])],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
   save('focus-benchmark-'+label,client_pid=child.pid);code=child.wait(timeout=35)
  result=json.loads(logpath.read_text());assert code==0 and result['fixture_passed'] and result['checksum_consistent']
  state['focus_benchmarks'][label]=dict(**result,alternating_old_new_order=True,cached_full_not_dma=True)
