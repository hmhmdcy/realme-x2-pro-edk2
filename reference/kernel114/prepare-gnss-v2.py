from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114')
text=(ref/'gnss-single-client.py').read_text().replace('k114-gnss-single-client','k114-gnss-single-client-v2').replace('115','116')
text=text.replace("['position-report','gnss-sv-info','nmea','engine-state','fix-session-state']","['position-report','gnss-sv-info','nmea','engine-state']")
(ref/'gnss-single-client-v2.py').write_text(text)
text=(ref/'probe-gnss-single-client.sh').read_text().replace('k114-gnss-single-client','k114-gnss-single-client-v2').replace('115','116')
(ref/'probe-gnss-single-client-v2.sh').write_text(text)
print('GNSS116_SINGLE_CLIENT_PROBE_WITH_IMPLEMENTED_SIGNALS_PREPARED')
