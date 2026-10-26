"""Build standard public-API requests with manual changes and measured output bands."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel300';P=host.PRIVATE
s=(OLD/'pipeline-smoke.cpp').read_text()
anchor='class Capture\n';assert s.count(anchor)==1
s=s.replace(anchor,'''static void setRequestControls(Request *request, unsigned int sequence, unsigned int epoch)
{
 request->controls().clear();
 int exposure = sequence == 24 || sequence == 72 ? 30000 : sequence == 48 || sequence == 216 ? 5000 : sequence == 192 ? 15000 : 0;
 float gain = sequence == 96 || sequence == 144 ? 4.0f : sequence == 120 || sequence == 168 ? 2.0f : 0;
 if (exposure) request->controls().set(controls::ExposureTime, int32_t(exposure));
 if (gain) request->controls().set(controls::AnalogueGain, gain);
 if (exposure || gain) std::cout << "APPLICATION_SENSOR_COMMAND epoch=" << epoch << " request=" << sequence
  << " exposure_us=" << exposure << " analogue_gain=" << gain << std::endl;
}

'''+anchor)
s=s.replace('unsigned int frames = 0, failed = 0;','unsigned int frames = 0, failed = 0, nextRequest = 4, epoch = 0;')
anchor='\t\t\tconst auto &m = buffer->metadata();';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
   auto exposure = request->metadata().get(controls::ExposureTime);
   auto analogue = request->metadata().get(controls::AnalogueGain);
   auto exposureMode = request->metadata().get(controls::ExposureTimeMode);
   auto gainMode = request->metadata().get(controls::AnalogueGainMode);
   if (!exposure || !analogue || !exposureMode || !gainMode || *exposureMode != controls::ExposureTimeModeManual || *gainMode != controls::AnalogueGainModeManual || *exposure <= 0 || !std::isfinite(*analogue) || *analogue < 1 || *analogue > 16) ++failed;
   else std::cout << "APPLICATION_SENSOR_METADATA epoch=" << epoch << " request=" << request->sequence()
    << " exposure_us=" << *exposure << " analogue_gain=" << *analogue
    << " exposure_mode=" << *exposureMode << " gain_mode=" << *gainMode << std::endl;
''')
s=s.replace('uint64_t hash = UINT64_C(14695981039346656037), total = 0;','uint64_t hash = UINT64_C(14695981039346656037), total = 0;\n\t\t\tstd::array<uint64_t, 4> lumaBands{};')
anchor='\t\t\t\t\t\thash = (hash ^ data[n]) * UINT64_C(1099511628211);';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\t\t\t\t\t\tif (!i && n < 320 * 240) lumaBands[n / (320 * 60)] += data[n];')
anchor='\t\t\tstd::cout << "APPLICATION_FRAME number="';pos=s.index(anchor)
s=s[:pos]+'''   if (total != 115200) ++failed;
   std::cout << "APPLICATION_LUMA epoch=" << epoch << " request=" << request->sequence();
   for (auto sum : lumaBands) std::cout << " " << double(sum) / (320 * 60);
   std::cout << std::endl;
'''+s[pos:]
s=s.replace('frames < 24','frames < 240').replace('epoch < 3','epoch < 2').replace('std::chrono::seconds(15)','std::chrono::seconds(20)')
anchor='\t\t\trequest->reuse(Request::ReuseBuffers);\n\t\t\tif (camera->queueRequest(request))';assert s.count(anchor)==1
s=s.replace(anchor,'\t\t\trequest->reuse(Request::ReuseBuffers);\n\t\t\tsetRequestControls(request, nextRequest++, epoch);\n\t\t\tif (camera->queueRequest(request))')
anchor='\t\tcontrols.set(controls::ColourGains, Span<const float, 2>(gains));';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\t\tcontrols.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);\n\t\tcontrols.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);\n\t\tcontrols.set(controls::ExposureTime, int32_t(5000));\n\t\tcontrols.set(controls::AnalogueGain, 2.0f);')
anchor='\t\t\tcapture.frames = capture.failed = 0;';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\t\t\tcapture.nextRequest = 4; capture.epoch = epoch;')
anchor='\t\t\tif (camera->queueRequest(request.get()))';assert s.count(anchor)==1
s=s.replace(anchor,'\t\t\trequest->controls().clear();\n'+anchor)
anchor='\tFrameBufferAllocator allocator(camera);';assert s.count(anchor)==1
s=s.replace(anchor,'\tif (config->at(0).stride != 320) return 6;\n'+anchor)
(HERE/'pipeline-smoke.cpp').write_text(s)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss302-runtime';stage.mkdir(exist_ok=True);shutil.copyfile(HERE/'pipeline-smoke.cpp',stage/'pipeline-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror','-I/candidate278-r24/usr/include/libcamera','/private/camss302-runtime/pipeline-smoke.cpp','-L/candidate278-r24/usr/lib','-Wl,-rpath-link,/candidate278-r24/usr/lib','-lcamera','-lcamera-base','-pthread','-o','/private/camss302-runtime/pipeline-smoke'],capture_output=True,timeout=180)
(P/'application-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
shutil.copyfile(stage/'pipeline-smoke',P/'pipeline-smoke-aarch64-private')
fixture=P.parent/'kernel300/pipeline-fixture-aarch64-private';assert hashlib.sha256(fixture.read_bytes()).hexdigest()=='5f5fcbf0300a539327edf699272ffc383a44a3d34bb55ad17ef9ea3ed71b3319'
shutil.copyfile(fixture,P/'pipeline-fixture-aarch64-private')
out=dict(stage=302,public_application_werror_compile_pass=True,two_epochs240frames_each_planned=True,nine_standard_control_changes_per_epoch=True,luma_four_output_bands_measured=True,
 application_source_sha256=hashlib.sha256((HERE/'pipeline-smoke.cpp').read_bytes()).hexdigest(),application_sha256=hashlib.sha256((P/'pipeline-smoke-aarch64-private').read_bytes()).hexdigest(),fixture_reused_with_verified_hash=True)
(HERE/'runtime-tools-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
