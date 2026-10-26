from pathlib import Path
import hashlib,json,urllib.request
P=Path('/mnt/e/edk2-samurai-out/kernel244/gnss-layouts');P.mkdir(mode=0o700,exist_ok=True);results={}
base='https://raw.githubusercontent.com/mobile-insight/mobileinsight-core/master/dm_collector_c/'
for name in ['gnss_gps_measurement_report.h','gnss_glonass_measurement_report.h','gnss_bds_measurement_report.h','gnss_gal_measurement_report.h','log_packet.cpp','log_packet.h']:
 try:
  b=urllib.request.urlopen(base+name,timeout=20).read();assert len(b)>100
  (P/name).write_bytes(b);results[name]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),url=base+name)
 except Exception as e:results[name]=dict(error=type(e).__name__)
(P/'manifest-private.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
