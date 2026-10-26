#include <fstream>
#include <sstream>
#include <functional>

static std::string read_text(const std::string &path)
{
	std::ifstream input(path);assert(input.good());std::stringstream s;s<<input.rdbuf();
	std::string out=s.str();while(!out.empty() && (out.back()=='\n' || out.back()=='\r'))out.pop_back();return out;
}
static size_t value_position(const std::string &text,const std::string &name)
{
	size_t p=text.find("\""+name+"\":");assert(p!=std::string::npos);p+=name.size()+3;
	while(p<text.size() && text[p]==' ')p++;
	return p;
}
static int64_t metric(const std::string &text,const std::string &name){return std::stoll(text.substr(value_position(text,name)));}
static bool flag(const std::string &text,const std::string &name){return text.compare(value_position(text,name),4,"true")==0;}
static const std::string device="/sys/bus/platform/devices/ac10000.icp/";
static const std::string parameters="/sys/module/qcom_camss_icp_a5_core/parameters/";
static unsigned parameter(const std::string &name){return std::stoul(read_text(parameters+name));}
static void arm()
{
	assert(!parameter("test_drop_frame_ack") && !parameter("test_dropped_frame_acks"));
	int fd=open((parameters+"test_drop_frame_ack").c_str(),O_WRONLY|O_CLOEXEC);assert(fd>=0 && write(fd,"1\n",2)==2);close(fd);
}
static void released()
{
	std::string s=read_text(device+"state");
	for(const char *name:{"backing_owned","cpu_enabled","irq_enabled","power_held","ipe_dma_pending","request_fw_mapped"})assert(!flag(s,name));
	for(const char *name:{"mapped_bytes","imported_buffers","imported_bytes","remaining_groups","remaining_domains","cleanup_error","pc_error","watchdogs","protocol_errors"})assert(!metric(s,name));
}
class Limit : public Object {public:bool expired=false;void timeout(){expired=true;}};
static void wait_for(const std::function<bool()> &done)
{
	Limit limit;Timer timer;timer.timeout.connect(&limit,&Limit::timeout);timer.start(std::chrono::seconds(20));
	while(!done() && !limit.expired)Thread::current()->eventDispatcher()->processEvents();
	assert(!limit.expired);timer.stop();
}
class Channel : public Object
{
public:
	CamssIpe ipe;
	FrameBuffer *input,*output;
	MappedFrameBuffer source,destination;
	unsigned good=0,bad=0,pending=0,serial=0;uint32_t input_crc=0;
	Channel(const char *node,std::shared_ptr<MediaDevice> media,FrameBuffer *in,FrameBuffer *out)
		:ipe(node,std::move(media)),input(in),output(out),source(in,MappedFrameBuffer::MapFlag::ReadWrite),destination(out,MappedFrameBuffer::MapFlag::ReadWrite)
	{assert(source.isValid() && destination.isValid());ipe.processed.connect(this,&Channel::done);}
	void submit(unsigned mode,bool zero_gamma=false)
	{
		assert(!pending);serial++;auto &m=input->_d()->metadata();m.status=FrameMetadata::FrameSuccess;
		m.sequence=200+serial;m.timestamp=1000000000000ULL+serial*1000000ULL;m.planes()[0].bytesused=640*480*3/2;
		pattern(source.planes()[0].data(),640,640,false);
		memset(destination.planes()[0].data(),0xa7,destination.planes()[0].size());input_crc=crc(source.planes()[0].data(),640*480*3/2);
		qcom_ipe_a5_frame_params p{};params_for(&p,mode);if(zero_gamma)p.flags|=QCOM_IPE_A5_GAMMA;
		assert(p.version==1 && (p.flags&QCOM_IPE_A5_LTM));pending=1;assert(!ipe.queue(input,output,&p));memset(&p,0x5a,sizeof(p));
	}
	void done(FrameBuffer *in,FrameBuffer *out,bool success)
	{
		assert(in==input && out==output && pending==1);pending=0;
		assert(input->metadata().sequence==200+serial && input->metadata().timestamp==1000000000000ULL+serial*1000000ULL);
		if(success)good++;else bad++;
		/* Failed image memory is inspected later, only after reset/join. */
	}
	void unchanged_input(){assert(input_crc==crc(source.planes()[0].data(),640*480*3/2));}
	void gray(unsigned expected)
	{
		const auto *p=destination.planes()[0].data();
		for(unsigned y=16;y<64;y++)for(unsigned x=0;x<640;x++)if(x%80>=16 && x%80<64)assert(p[y*640+x]==expected);
		unchanged_input();
	}
	void untouched(){for(uint8_t b:destination.planes()[0])assert(b==0xa7);unchanged_input();}
	void black()
	{
		const auto *p=destination.planes()[0].data();for(unsigned i=0;i<640*480;i++)assert(p[i]==0);
		for(unsigned i=640*480;i<640*480*3/2;i++)assert(p[i]==128);
		for(unsigned i=640*480*3/2;i<destination.planes()[0].size();i++)assert(p[i]==0xa7);
		unchanged_input();
	}
};

int main(int argc,char **argv)
{
	assert(argc==4);auto media=std::make_shared<MediaDevice>(argv[2]);assert(!media->populate() && media->driver()=="qcom-ipe-a5" && media->acquire());
	V4L2DeviceFormat f;f.fourcc=V4L2PixelFormat(V4L2_PIX_FMT_NV12);f.size=Size(640,482);f.planesCount=1;f.planes[0].bpl=640;
	V4L2M2MDevice exporter(argv[1]);assert(!exporter.open() && !exporter.output()->setFormat(&f));
	std::vector<std::unique_ptr<FrameBuffer>> exported,buffers;assert(exporter.output()->allocateBuffers(8,&exported)>=8);
	for(const auto &b:exported){auto p=b->planes();unsigned length=0;for(const auto &plane:p){assert(plane.fd==p[0].fd && plane.offset==length);length+=plane.length;}
		std::vector<FrameBuffer::Plane> flat={{p[0].fd,0,length}};buffers.push_back(std::make_unique<FrameBuffer>(flat));}
	exporter.close(); /* Exported plane FDs keep backing, not this context. */
	f.size.height=480;f.planes[0].size=640*480*3/2;
	Channel a(argv[1],media,buffers[0].get(),buffers[1].get()),b(argv[1],media,buffers[2].get(),buffers[3].get());
	V4L2M2MDevice keeper(argv[1]);assert(!keeper.open()); /* Pre-fault idle consumer deliberately held. */
	assert(!a.ipe.start(f,1) && !b.ipe.start(f,1));
	a.submit(3);wait_for([&]{return a.good==1;});a.gray(128);
	b.submit(3);wait_for([&]{return b.good==1;});b.gray(128);
	std::string warm=read_text(device+"m2m_status"),warm_core=read_text(device+"state");
	assert(metric(warm,"completed")==2 && metric(warm_core,"session_creates")==2 && metric(warm_core,"session_peak")==2);
	arm();auto begin=std::chrono::steady_clock::now();
	a.submit(4,true);b.submit(3);wait_for([&]{return a.bad==1 && b.bad==1;});
	a.ipe.stop();b.ipe.stop();
	double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();assert(elapsed>=4.5 && elapsed<12);
	assert(a.good==1 && b.good==1 && !a.pending && !b.pending);released();
	std::string failed=read_text(device+"m2m_status");assert(flag(failed,"fatal") && !flag(failed,"running") && !flag(failed,"pinned"));
	assert(metric(failed,"users")==1 && metric(failed,"first_error")==-110 && metric(failed,"completed")==2);
	assert(parameter("test_drop_frame_ack")==0 && parameter("test_dropped_frame_acks")==1);
	a.black();b.untouched();dump(std::string(argv[3])+"/timed-out-black-private.nv12",a.destination.planes()[0].data(),640*480*3/2);
	Channel blocked(argv[1],media,buffers[4].get(),buffers[5].get());assert(!blocked.ipe.start(f,1));
	auto blocked_begin=std::chrono::steady_clock::now();blocked.submit(3,true);
	wait_for([&]{return blocked.bad==1;});
	double blocked_seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-blocked_begin).count();
	assert(blocked_seconds<1.0);blocked.ipe.stop();released();blocked.untouched();assert(!blocked.good);
	std::string gated=read_text(device+"m2m_status");assert(flag(gated,"fatal") && metric(gated,"users")==1);
	keeper.close();std::string closed=read_text(device+"m2m_status");assert(!flag(closed,"fatal") && metric(closed,"users")==0);
	Channel healthy(argv[1],media,buffers[6].get(),buffers[7].get());assert(!healthy.ipe.start(f,1));healthy.submit(4);
	wait_for([&]{return healthy.good==1;});healthy.ipe.stop();released();healthy.gray(64);assert(!healthy.bad);
	dump(std::string(argv[3])+"/recovered-la1024-private.nv12",healthy.destination.planes()[0].data(),640*480*3/2);
	std::string recovered=read_text(device+"m2m_status"),core=read_text(device+"state");
	assert(metric(recovered,"completed")==3 && metric(recovered,"direct_completed")==3 && metric(recovered,"failed")>=2 && metric(recovered,"first_error")==-110);
	assert(metric(recovered,"jobs")==metric(recovered,"completed")+metric(recovered,"failed")+metric(recovered,"cancelled"));
	assert(metric(recovered,"users")==0 && !flag(recovered,"fatal") && !flag(recovered,"running"));
	std::cout<<"{\"case\":\"typed-iq-lost-valid-ack\",\"actual_libcamera418\":true,\"elapsed_seconds\":"<<elapsed
		<<",\"dropped_ack_count\":1,\"combined_ltm_gamma_timeout\":true,\"false_callbacks\":3,\"successful_callbacks\":3,\"idle_consumer_preserves_fatal_gate\":true,\"blocked_callback_seconds\":"<<blocked_seconds
		<<",\"warm\":"<<warm<<",\"warm_core\":"<<warm_core<<",\"failed\":"<<failed<<",\"gated\":"<<gated<<",\"closed\":"<<closed<<",\"recovered\":"<<recovered<<",\"core\":"<<core<<",\"passed\":true}"<<std::endl;
	media->release();return 0;
}
