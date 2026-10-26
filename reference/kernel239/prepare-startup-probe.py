"""Two stop/start cycles on one camera/IPA instance, preserving per-run metadata."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent
text=(R/'fixed-rgb-probe.cpp').read_text()
a=text.index('    void print() const\n');b=text.index('\nprivate:',a);printing=text[a:b]
printing=printing.replace('void print()','std::string json()').replace('std::cout','out').replace('    {\n        out <<','    {\n        std::ostringstream out;\n        out <<',1).replace('out << "]}\\n";','out << "]}";\n        return out.str();')
assert 'return out.str();' in printing;text=text[:a]+printing+text[b:]
text=text.replace('    int status = 1;','    int status = 1;\n    std::vector<std::string> runSummaries;')
a=text.index('        for (const auto &buffer : allocator->buffers(stream)) {');b=text.index('        pattern = ',a);create=text[a:b]
text=text[:a]+text[b:]
a=text.index('        pattern = std::make_unique<PatternGuard>');b=text.index('        status = 0;',a)
old=text[a:b]
body_start=old.index('        capture = ');body_end=old.index('        require(pattern->restore()')
body=old[body_start:body_end]
# The same Camera and configured buffers remain acquired; each run gets fresh Requests.
replacement='        pattern = std::make_unique<PatternGuard>(argv[1], selected);\n        for (unsigned int run = 0; run < 2; ++run) {\n            requests.clear();\n'+create+body+'            runSummaries.push_back(capture->json());\n            require(complete, "twelve complete startup frames");\n            capture.reset();\n        }\n        require(pattern->restore(), "restore sensor pattern after both runs");\n        pattern.reset();\n'
text=text[:a]+replacement+text[b:]
old='    if (capture) capture->print();';assert text.count(old)==1
text=text.replace(old,'''    if (capture) runSummaries.push_back(capture->json());
    std::cout << "{\\\"runs\\\":[";
    for (size_t i = 0; i < runSummaries.size(); ++i) { if (i) std::cout << ','; std::cout << runSummaries[i]; }
    std::cout << "]}\\n";''')
assert text.count('camera->configure(')==1 and 'run < 2' in text
(R/'startup-probe.cpp').write_text(text)
runner=(R/'native-fixed-rgb.py').read_text().replace('k239-fixed-rgb-r14','k239-r15-startup').replace('/fixed-rgb-probe239','/startup-probe239').replace('k239_fixed_rgb_controls','k239_r15_startup').replace('/run/samurai-camera238-r14','/run/samurai-camera239-r15').replace('fixed12-frame-rgb-debug-trace-armed','two-startup12-frame-r15-debug-trace-armed')
old="assert json.loads((root/'k238-candidate-permissions-fix/summary.json').read_text())['uid10000_cpu_config_read_verified']";assert runner.count(old)==1
runner=runner.replace(old,"assert json.loads((root/'k239-candidate-stage/summary.json').read_text())['ram_candidate_staged']")
old=" frames=data.get('frames',[]) if data else []";assert runner.count(old)==1
runner=runner.replace(old," runs=data.get('runs',[]) if data else [];frames=[dict(f,run_index=i) for i,run in enumerate(runs) for f in run['frames']];geometry=runs[0] if runs else {}")
runner=runner.replace("stream_geometry={k:data[k] for k in ['width','height','stride']} if data else {},frames=frames,", "stream_geometry={k:geometry[k] for k in ['width','height','stride']} if geometry else {},same_camera_two_start_stop_runs=True,run_count=len(runs),frames=frames,")
runner=runner.replace('len(frames)==12','len(frames)==24 and len(runs)==2 and all(len(run[\'frames\'])==12 for run in runs)')
ast.parse(runner);(R/'native-r15-startup.py').write_text(runner)
start=(R/'start-fixed-rgb.py').read_text().replace('fixed-rgb-build-validation.json','startup-build-validation.json').replace('fixed-rgb-probe239','startup-probe239').replace('native-fixed-rgb.py','native-r15-startup.py').replace('k239-fixed-rgb-r14','k239-r15-startup').replace('fixed-rgb-launch','r15-startup-launch').replace('fixed12 RGB diagnostic running once','r15 two-startup RGB diagnostic running once')
ast.parse(start);(R/'start-r15-startup.py').write_text(start)
poll=(R/'poll-fixed-rgb.py').read_text().replace('k239-fixed-rgb-r14','k239-r15-startup').replace('fixed-rgb-validation.json','r15-startup-validation.json').replace('fixed-rgb-poll','r15-startup-poll').replace('fixed-rgb-parameter-log-lines-private.json','r15-startup-parameter-log-lines-private.json').replace('fixed12 RGB diagnostic terminal','r15 two-startup RGB diagnostic terminal')
poll=poll.replace("[('debayer','Debayer parameters:'),", "[('processing','Processing frame '),('debayer','Debayer parameters:'),")
ast.parse(poll);(R/'poll-r15-startup.py').write_text(poll)
print('Prepared same-camera stop/start regression: two runs of12 fixed frames')
