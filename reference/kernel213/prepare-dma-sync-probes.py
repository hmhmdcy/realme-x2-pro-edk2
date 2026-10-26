from pathlib import Path
here=Path(__file__).resolve().parent
for original in ['raw-dark','csid-known-input']:
    text=(here/(original+'-probe.cpp')).read_text().replace('#include <linux/videodev2.h>','#include <linux/videodev2.h>\n#include <linux/dma-buf.h>')
    start=text.index('class PatternGuard {')
    text=text[:start]+'''class DmaReadGuard {
public:
    explicit DmaReadGuard(int fd) : fd_(fd)
    {
        dma_buf_sync sync{};
        sync.flags = DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ;
        active_ = ioctl(fd_, DMA_BUF_IOCTL_SYNC, &sync) == 0;
    }
    bool valid() const { return active_; }
    bool finish()
    {
        if (!active_) return false;
        dma_buf_sync sync{};
        sync.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ;
        bool success = ioctl(fd_, DMA_BUF_IOCTL_SYNC, &sync) == 0;
        active_ = false;
        return success;
    }
    ~DmaReadGuard() { if (active_) finish(); }
private:
    int fd_;
    bool active_ = false;
};

''' + text[start:]
    target='''        void *mapping = mmap(nullptr, plane.offset + plane.length, PROT_READ,'''
    replacement='''        DmaReadGuard sync(plane.fd.get());
        if (!sync.valid()) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true;
            ready_.notify_all();
            return;
        }
        void *mapping = mmap(nullptr, plane.offset + plane.length, PROT_READ,'''
    assert text.count(target)==1;text=text.replace(target,replacement)
    target='''        const double mean = double(sum) / active.size();'''
    replacement='''        if (!sync.finish()) {
            std::lock_guard<std::mutex> lock(mutex_);
            failed_ = true;
            ready_.notify_all();
            return;
        }
        const double mean = double(sum) / active.size();'''
    assert text.count(target)==1;text=text.replace(target,replacement)
    (here/(original+'-sync-probe.cpp')).write_text(text)
    builder=(here/('build-raw-dark-probe.py' if original=='raw-dark' else 'build-csid-probe.py')).read_text()
    builder=builder.replace(original+'-probe',original+'-sync-probe').replace('no_product_replacement=True','no_product_replacement=True,dma_buf_sync_start_end_read=True')
    (here/('build-'+original+'-sync-probe.py')).write_text(builder)
    runner=(here/('run-raw-dark-probe.py' if original=='raw-dark' else 'run-csid-known-input-probe.py')).read_text()
    runner=runner.replace(original+'-probe',original+'-sync-probe').replace("tag=variant+'-'+kind+'-p'+str(pattern)","tag=variant+'-'+kind+'-p'+str(pattern)+'-sync'").replace("+'-r2'","+'-sync'")
    runner=runner.replace("test_pattern_and_sensor_controls_restored=True", "test_pattern_and_sensor_controls_restored=True,dma_buf_sync_start_end_read=True")
    (here/('run-'+original+'-sync-probe.py')).write_text(runner)
