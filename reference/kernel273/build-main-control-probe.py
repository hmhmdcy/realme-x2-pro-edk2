"""Build a GW1 same-request RAW/RGB probe from the verified control probe."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
text=(R.parent/'kernel271/telephoto-control-probe.cpp').read_text()
changes=[('/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d','/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10'),
 ('s5k3m5 8-002d','s5kgw1 6-0010'),('"s5k3m5"','"s5kgw1"'),
 ('2104, 1560','4608, 3456'),('2104,1560','4608,3456'),('formats::SGRBG10_CSI2P','formats::SGBRG10_CSI2P'),
 ('*gain <= 16.0f','*gain <= 32.0f'),
 ('{{{2000,1}, {8000,1}, {32000,1}, {32000,2}, {32000,4}, {32000,8}, {32000,16}, {32000,1}}}',
  '{{{2000,1}, {8000,1}, {32000,1}, {32000,1.5}, {32000,2}, {32000,4}, {32000,8}, {32000,1}}}')]
for a,b in changes:assert a in text,a;text=text.replace(a,b)
# GW1 has no verified test-pattern control. Do not add or fake one for the test.
start=text.index('class PatternGuard {');brace=text.index('{',start);depth=1;i=brace+1
while depth:depth+=int(text[i]=='{')-int(text[i]=='}');i+=1
assert text[i]==';';text=text[:start]+text[i+1:]
for line in ['    std::unique_ptr<PatternGuard> pattern;\n','        pattern = std::make_unique<PatternGuard>(argv[1], 0);\n',
 '        require(pattern->restore(), "restore paired sensor pattern"); pattern.reset();\n','    if (pattern && !pattern->restore()) status = 1;\n']:
 assert text.count(line)==1;text=text.replace(line,'')
text=text.replace('    pattern.reset(); requests.clear(); allocator.reset();','    requests.clear(); allocator.reset();')
p=R/'main-control-probe.cpp';assert not p.exists();p.write_text(text)
name='main-control-probe273';shutil.copyfile(p,SDK/'private'/(name+'.cpp'));assert not (SDK/'private'/name).exists()
prefix='/candidate273-r21'
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread',
 '-I'+prefix+'/usr/include/libcamera','/private/'+name+'.cpp','-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib',
 '-lcamera','-lcamera-base','-o','/private/'+name],capture_output=True,timeout=180)
(host.PRIVATE/'main-control-probe-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH='+prefix+'/usr/lib','/private/'+name,'--self-test'],capture_output=True,timeout=15,check=True)
assert json.loads(q.stdout)['raw10_known_wire_vector_passed']
binary=host.PRIVATE/name;shutil.copyfile(SDK/'private'/name,binary)
report=dict(stage=273,source_sha256=hashlib.sha256(text.encode()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
 werror_clean=True,raw10_known_wire_vector_passed=True,manual_plan=[[2000,1],[8000,1],[32000,1],[32000,1.5],[32000,2],[32000,4],[32000,8],[32000,1]],
 frames_per_phase=12,automatic_frames=180,no_pixels_written_by_probe=True,no_test_pattern_control_added_or_used=True)
(R/'main-control-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
