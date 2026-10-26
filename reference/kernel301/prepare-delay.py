"""Build a bounded public-API timing application without changing the tested IPA."""
from pathlib import Path
import hashlib,io,json,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel300';P=host.PRIVATE
s=(OLD/'pipeline-smoke.cpp').read_text()
s=s.replace('/* Real application requests, including restart without reconfiguration. */','/* Test-only SOF-timed exposure/gain measurement; normal libcamera requests. */')
s=s.replace('#include <chrono>','#include <chrono>\n#include <cerrno>\n#include <fcntl.h>\n#include <poll.h>\n#include <sys/prctl.h>\n#include <sys/wait.h>')
anchor='class Capture\n';assert s.count(anchor)==1
s=s.replace(anchor,r'''/* Child uses only async-signal-safe operations between fork and exec. */
class Stepper
{
public:
	pid_t pid = -1;
	int status = -1;
	bool start(const char *path)
	{
		int fds[2];
		if (pipe2(fds, O_CLOEXEC)) return false;
		const pid_t parent = getpid();
		std::string descriptor = std::to_string(fds[1]);
		pid = fork();
		if (!pid) {
			close(fds[0]);
			if (prctl(PR_SET_PDEATHSIG, SIGTERM) || getppid() != parent ||
			    fcntl(fds[1], F_SETFD, 0)) _exit(126);
			execl(path, path, descriptor.c_str(), nullptr);
			_exit(127);
		}
		close(fds[1]);
		bool ready = false;
		const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
		while (pid > 0 && !interrupted && std::chrono::steady_clock::now() < deadline) {
			pollfd item{ fds[0], POLLIN, 0 };
			int ret = poll(&item, 1, 100);
			if (ret < 0 && errno == EINTR) continue;
			if (ret < 0) break;
			if (!ret) continue;
			char byte = 0;
			ready = read(fds[0], &byte, 1) == 1 && byte == 'R';
			break;
		}
		close(fds[0]);
		return ready;
	}
	bool finish()
	{
		for (unsigned int n = 0; pid > 0 && n < 200; ++n) {
			pid_t ret = waitpid(pid, &status, WNOHANG);
			if (ret == pid) { pid = -1; return WIFEXITED(status) && !WEXITSTATUS(status); }
			if (ret < 0 && errno != EINTR) { pid = -1; return false; }
			usleep(10000);
		}
		return false;
	}
	~Stepper()
	{
		if (pid > 0) {
			kill(pid, SIGTERM);
			if (!finish() && pid > 0) {
				kill(pid, SIGKILL);
				while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
			}
		}
	}
};

'''+anchor)
s=s.replace('if (argc != 2)','if (argc != 3)').replace('frames < 24','frames < 240').replace('epoch < 3','epoch < 1').replace('std::chrono::seconds(15)','std::chrono::seconds(20)')
anchor='\tint result = 0;';assert s.count(anchor)==1
s=s.replace(anchor,'\tStepper stepper;\n\tif (!stepper.start(argv[2])) { std::cout << "APPLICATION_FAILURE stage=stepper-ready" << std::endl; return 13; }\n'+anchor)
anchor='\trequests.clear();';assert s.count(anchor)==1
s=s.replace(anchor,'\tif (!stepper.finish()) result = 14;\n'+anchor)
(HERE/'delay-capture.cpp').write_text(s)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss301-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'delay-capture.cpp',stage/'delay-capture.cpp')
commands=[
 ['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror','-I/candidate278-r24/usr/include/libcamera','/private/camss301-runtime/delay-capture.cpp','-L/candidate278-r24/usr/lib','-Wl,-rpath-link,/candidate278-r24/usr/lib','-lcamera','-lcamera-base','-pthread','-o','/private/camss301-runtime/delay-capture'],
 ['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(HERE/'control-stepper.c'),'-o',str(P/'control-stepper-aarch64-private')],
]
for i,cmd in enumerate(commands):
 q=subprocess.run(cmd,capture_output=True,timeout=180);(P/f'compile-{i}-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run(['qemu-aarch64',str(P/'control-stepper-aarch64-private'),'3'],capture_output=True,timeout=10);assert q.returncode==3
shutil.copyfile(stage/'delay-capture',P/'delay-capture-aarch64-private')
previous=json.loads((OLD/'ipa-bundle-r4-validation.json').read_text());raw=(P.parent/'kernel300'/previous['archive_file']).read_bytes()
assert hashlib.sha256(raw).hexdigest()==previous['archive_sha256']
files={}
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
 assert set(tar.getnames())==set(previous['files'])
 for name in tar.getnames():
  data=tar.extractfile(name).read();assert hashlib.sha256(data).hexdigest()==previous['files'][name]['sha256'];files[name]=data
files['bin/pipeline-smoke']=(P/'delay-capture-aarch64-private').read_bytes()
files['bin/control-stepper']=(P/'control-stepper-aarch64-private').read_bytes()
archive=P/'delay-bundle-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,data in files.items():
  item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o600 if name.startswith('profile/') or name.endswith('.sign') else 0o700;tar.addfile(item,io.BytesIO(data))
report=dict(stage=301,archive_file=archive.name,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),archive_bytes=archive.stat().st_size,
 compile_werror_pass=True,wrong_kernel_guard_exit=q.returncode,tested300_libraries_module_signature_proxy_fixture_profile_reused=True,
 no_sdk_kernel_or_product_package_changes=True,files={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in files.items()},
 source_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['control-stepper.c','delay-capture.cpp']})
(HERE/'delay-bundle-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
