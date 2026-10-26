from pathlib import Path
p=Path(__file__).resolve().parent
for source,dest in [('prepare-live-native-r3.py','prepare-live-native-r4.py'),('build-live-overlay-r3.py','build-live-overlay-r4.py'),('probe-front-driver-r3.py','probe-front-driver-r4.py')]:
 s=(p/source).read_text().replace('k196-live-prepare-r3','k196-live-prepare-r4').replace('live-input-r3-private','live-input-r4-private').replace('k196-front-probe-r3','k196-front-probe-r4');(p/dest).write_text(s)
s=(p/'finalize-first-attempt.py').read_text().replace("root/'k196-front-probe'","root/'k196-front-probe-r3'");(p/'finalize-third-attempt.py').write_text(s)
print('Fourth attempt uses required OF clock retrieval with all prior evidence retained')
