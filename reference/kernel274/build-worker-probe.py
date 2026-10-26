"""Compare original callback statistics with identical full statistics off-thread."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
text=(R.parent/'kernel273/main-control-probe.cpp').read_text()
text=text.replace('#include <map>','#include <map>\n#include <deque>\n#include <thread>')
text=text.replace('static bool automaticMode = false;','static bool automaticMode = false;\nstatic bool workerMode = true;\nstatic bool diagnosticOnly = false;')
a='''        : camera_(camera), rgb_(rgb), raw_(raw) {}
'''
b='''        : camera_(camera), rgb_(rgb), raw_(raw), worker_([this] { workerLoop(); }) {}
    ~PairedCapture() { stopWorker(); }
    void stopWorker()
    {
        { std::lock_guard lock(workMutex_); stopping_ = true; }
        workReady_.notify_all();
        if (worker_.joinable()) worker_.join();
    }
    void workerLoop()
    {
        for (;;) {
            Request *request;
            {
                std::unique_lock lock(workMutex_);
                workReady_.wait(lock, [this] { return stopping_ || !work_.empty(); });
                if (work_.empty() && stopping_) return;
                request = work_.front(); work_.pop_front();
            }
            processCompleted(request);
        }
    }
'''
assert text.count(a)==1;text=text.replace(a,b)
a='''    void completed(Request *request)
    {
        try { checked(request); }
'''
b='''    void completed(Request *request)
    {
        if (request->status() == Request::RequestCancelled) return;
        if (workerMode) {
            { std::lock_guard lock(workMutex_); work_.push_back(request); }
            workReady_.notify_one();
        } else {
            processCompleted(request);
        }
    }
    void processCompleted(Request *request)
    {
        try { checked(request); }
'''
assert text.count(a)==1;text=text.replace(a,b)
a='''            require(std::abs(*exposure - expected.first) <= 40 && std::abs(*gain - expected.second) < 0.03f,
                    "stable captured metadata matches manual phase");'''
b='''            const bool matches = std::abs(*exposure - expected.first) <= 40 &&
                                 std::abs(*gain - expected.second) < 0.03f;
            if (!matches) {
                ++mismatches_;
                std::cerr << "CONTROL_MISMATCH queued=" << index << " sof=" << cm.sequence
                          << " expected_us=" << expected.first << " actual_us=" << *exposure
                          << " expected_gain=" << expected.second << " actual_gain=" << *gain << '\\n';
            }
            if (!diagnosticOnly)
                require(matches, "stable captured metadata matches manual phase");'''
assert text.count(a)==1;text=text.replace(a,b)
text=text.replace('''                  << ",\\\"frames\\\":[";''','''                  << ",\\\"strict_phase_mismatches\\\":" << mismatches_
                  << ",\\\"worker_mode\\\":" << (workerMode ? "true" : "false")
                  << ",\\\"frames\\\":[";''')
assert '<< mismatches_' in text
a='    std::vector<std::string> frames_;'
b=a+'''
    unsigned int mismatches_ = 0;
    std::mutex workMutex_;
    std::condition_variable workReady_;
    std::deque<Request *> work_;
    bool stopping_ = false;
    std::thread worker_;'''
assert text.count(a)==1;text=text.replace(a,b)
a='(std::string(argv[8]) != "manual" && std::string(argv[8]) != "auto")) return 2;'
b='(std::string(argv[8]) != "manual-direct" && std::string(argv[8]) != "manual-worker" && std::string(argv[8]) != "auto-worker")) return 2;'
assert text.count(a)==1;text=text.replace(a,b)
text=text.replace('automaticMode = std::string(argv[8]) == "auto";','automaticMode = std::string(argv[8]) == "auto-worker";\n    workerMode = std::string(argv[8]) != "manual-direct";\n    diagnosticOnly = !workerMode;')
a='    requests.clear(); allocator.reset();'
assert text.count(a)==1;text=text.replace(a,'    if (capture) capture->stopWorker();\n'+a)
# Keep failed/canceled buffers alive until the statistics worker has drained.
assert text.index('capture->stopWorker();')<text.index('requests.clear();')
source=R/'main-worker-probe.cpp';assert not source.exists();source.write_text(text)
name='main-worker-probe274';assert not (SDK/'private'/name).exists();shutil.copyfile(source,SDK/'private'/(name+'.cpp'))
prefix='/candidate273-r21'
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread',
 '-I'+prefix+'/usr/include/libcamera','/private/'+name+'.cpp','-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib',
 '-lcamera','-lcamera-base','-o','/private/'+name],capture_output=True,timeout=180)
(host.PRIVATE/'worker-probe-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH='+prefix+'/usr/lib','/private/'+name,'--self-test'],capture_output=True,timeout=20,check=True)
assert json.loads(q.stdout)['raw10_known_wire_vector_passed']
binary=host.PRIVATE/name;shutil.copyfile(SDK/'private'/name,binary)
report=dict(stage=274,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
 werror_clean=True,raw10_known_wire_vector_passed=True,full_frame_statistics_unchanged=True,manual_plan_unchanged=True,
 strict_worker_assertion_unchanged=True,direct_mode_records_all_mismatches=True,no_product_driver_or_library_changes=True,
 buffer_and_request_lifetimes_retained_until_worker_join=True,phone_unchanged=True)
(R/'worker-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
