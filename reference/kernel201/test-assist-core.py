from pathlib import Path
import hashlib,importlib.util,json,urllib.request
ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('assist',ref/'samurai-gnss-assist.py');assist=importlib.util.module_from_spec(spec);spec.loader.exec_module(assist)
now=1792044000
assert not assist.validity_current(1790928000,168,now)
assert assist.validity_current(1792040400,168,now)
for start,hours,clock,expected in [(100,1,100,True),(100,1,3699,True),(100,1,3700,False),(100,1,99,False),(100,0,100,False),(100,-1,100,False),(100,100000,100,False)]:assert assist.validity_current(start,hours,clock)==expected
assert assist.validity_current(100,65535,100)
assert assist.tls_url('http://global.example/xtra.bin')=='https://global.example/xtra.bin'
for url in ['ftp://global.example/xtra.bin','https://u:p@global.example/xtra.bin','https://global.example/xtra.bin?key=x','https://global.example/xtra.bin#x','/xtra.bin']:
 try:assist.tls_url(url)
 except ValueError:pass
 else:raise AssertionError(url)
cases=[]
def scenario(name,before,expected_status,*,download_error=False,allowed=True,after=None,inject_error=False,query_error=False,servers=None):
 calls=[]
 def download(url,index):
  calls.append(('download',index))
  if download_error:raise OSError('network unavailable')
  return b'global-data'
 def inject(data):
  assert data==b'global-data';calls.append(('inject',))
  if inject_error:raise RuntimeError('QMI failure')
 def query():
  calls.append(('query',))
  if query_error:raise RuntimeError('readback failed')
  return after or dict(start=now-1,hours=168)
 try:r=assist.refresh_data(before,servers or ['http://global.example/a','http://global.example/b'],query,download,inject,lambda:allowed,lambda:now)
 except RuntimeError:
  assert expected_status=='exception';r={'status':'exception'}
 assert r['status']==expected_status,(name,r)
 cases.append(dict(name=name,status=r['status'],calls=calls));return r,calls
current=dict(start=now-1,hours=168);old=dict(start=1790928000,hours=168)
r,c=scenario('already current',current,'current');assert c==[] and r['injection_count']==0
r,c=scenario('expired refresh',old,'refreshed');assert c==[('download',0),('inject',),('query',)]
r,c=scenario('future start is not current',dict(start=now+3600,hours=168),'refreshed');assert r['injection_count']==1
r,c=scenario('transport ACK does not prove validity',old,'not-current-after-injection',after=old);assert c==[('download',0),('inject',),('query',)]
r,c=scenario('all downloads fail',old,'download-failed',download_error=True);assert r['injection_count']==0 and c==[('download',0),('download',1)]
r,c=scenario('client stops while downloading',old,'inactive',allowed=False);assert c==[('download',0)]
r,c=scenario('injection failure never retries another server',old,'exception',inject_error=True);assert c==[('download',0),('inject',)]
r,c=scenario('readback failure never reports current',old,'exception',query_error=True);assert c==[('download',0),('inject',),('query',)]
r,c=scenario('credential URL skipped',old,'refreshed',servers=['https://u:p@global.example/a','http://global.example/b']);assert c==[('download',1),('inject',),('query',)]
r,c=scenario('zero duration is not validity',dict(start=now,hours=0),'refreshed');assert r['injection_count']==1
payload=b'global-orbit-data';digest=hashlib.sha256(payload).hexdigest();assert assist.validate_payload(payload,{},now)==digest
for data,rejected,clock in [(b'',{},now),(b'  <!DOCTYPE html>',{},now),(b'<html>error',{},now),(b'x'*(5*1024*1024+1),{},now),(payload,{digest:old},now),(payload,{digest:dict(start=now+3600,hours=168)},now)]:
 try:assist.validate_payload(data,rejected,clock)
 except ValueError:pass
 else:raise AssertionError('Rejected payload accepted')
assert assist.validate_payload(payload,{digest:dict(start=now+3600,hours=168)},now+3600)==digest
for url in ['http://global.example/data','https://global.example/data?key=x','https://u:p@global.example/data']:
 try:assist.HttpsOnlyRedirect().redirect_request(urllib.request.Request('https://global.example/old'),None,302,'Found',{},url)
 except ValueError:pass
 else:raise AssertionError('Unapproved redirect accepted')
report=dict(stage=201,window_cases=10,url_cases=6,payload_cases=8,redirect_rejections=3,flow_cases=cases,old191_window_rejected=True,absolute_epoch_and_end_boundary_checked=True,known_bad_payload_and_future_window_reconsideration_checked=True)
(ref/'assist-core-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=201,window_cases=10,url_cases=6,payload_cases=8,flow_cases=len(cases),all_passed=True)))
