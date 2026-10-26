"""Prepare, without installing, a first-open logger for measured RF/clock evidence."""
from pathlib import Path
import hashlib,importlib.util,json,re
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel245');source=(R.parent/'kernel244/diag_transport_boot.py').read_text()
codes=(0x1477,0x1478,0x147e,0x147f,0x1480,0x1516,0x1596,0x1635,0x1756,0x1886)
header_bytes=(P.parent/'kernel244/protocol-source/log_codes.h').read_bytes();header=header_bytes.decode('latin1');names=['LOG_GNSS_GPS_MEASUREMENT_REPORT_C','LOG_GNSS_CLOCK_REPORT_C','LOG_GNSS_PRX_RF_HW_STATUS_REPORT_C','LOG_GNSS_DRX_RF_HW_STATUS_REPORT_C','LOG_GNSS_GLONASS_MEASUREMENT_REPORT_C','LOG_GNSS_CONFIGURATION_STATE_C','LOG_GNSS_WWAN_WLAN_IMD_JAMMER_STATUS_C','LOG_GNSS_SPECTRUM_ANALYZER_JAMMER_MEASUREMENTS_C','LOG_GNSS_BDS_MEASUREMENT_REPORT_C','LOG_GNSS_GAL_MEASUREMENT_REPORT_C']
verified={}
for name,code in zip(names,codes):
 line=next(x for x in header.splitlines() if x.startswith('#define '+name+' '));raw=int(re.search(r'0x([0-9A-Fa-f]+)',line).group(1),16);assert raw+0x1000==code;verified[name]=code
assert 'GNSS_LOG_CODES=(0x1477,0x1480,0x1756,0x1886)' in source;source=source.replace('GNSS_LOG_CODES=(0x1477,0x1480,0x1756,0x1886)','GNSS_LOG_CODES='+repr(codes)).replace('8*1024*1024','24*1024*1024').replace('self.records>8192','self.records>32768').replace('gnss_mask_only_four_verified_ids','gnss_mask_only_ten_verified_ids')
source=source.replace('Optional logging changes exactly four GNSS log bits','Optional logging changes exactly ten verified GNSS log bits');compile(source,'diag_transport_rf.py','exec');(R/'diag_transport_rf.py').write_text(source)
spec=importlib.util.spec_from_file_location('diag245rf',R/'diag_transport_rf.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);result=m.regression();assert list(m.GNSS_LOG_CODES)==sorted(codes)
report=dict(stage=245,library_prepared_not_installed=True,log_codes=verified,raw_record_bound=32768,raw_byte_bound=24*1024*1024,regression=result,header_sha256=hashlib.sha256(header_bytes).hexdigest(),no_rf_nv_or_calibration_command_api=True)
(R/'rf-library-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
