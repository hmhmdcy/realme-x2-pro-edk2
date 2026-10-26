#include "full_ownership_trace.h"
#include <cassert>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <new>
#include <sys/stat.h>
#include <string>

static std::atomic<uint64_t> allocations{0};
static std::atomic<bool> failNothrow{false};
void *operator new(std::size_t n)
{
    ++allocations;
    if (void *p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void *operator new(std::size_t n, const std::nothrow_t &) noexcept
{
    ++allocations;
    if (failNothrow.exchange(false))
        return nullptr;
    return std::malloc(n ? n : 1);
}
void *operator new[](std::size_t n, const std::nothrow_t &tag) noexcept
{ return ::operator new(n, tag); }
void operator delete(void *p) noexcept { std::free(p); }
void operator delete[](void *p) noexcept { std::free(p); }
void operator delete(void *p, std::size_t) noexcept { std::free(p); }
void operator delete[](void *p, std::size_t) noexcept { std::free(p); }
void operator delete(void *p, const std::nothrow_t &) noexcept { std::free(p); }
void operator delete[](void *p, const std::nothrow_t &) noexcept { std::free(p); }

using namespace libcamera::camss_diag;

int main(int argc, char **argv)
{
    assert(argc == 2);
    Event event{};
    event.type = uint16_t(EventType::PixSof);
    Ring<4> ring;
    ring.push(event);
    assert(!ring.active() && ring.total() == 0);
    failNothrow = true;
    assert(!ring.prepare() && !ring.active());
    assert(ring.prepare());
    uint64_t before = allocations;
    for (unsigned int i = 1; i <= 10000; ++i) {
        event.sof = i; event.hardwareNs = uint64_t(i)*33333333;
        ring.push(event);
    }
    assert(allocations == before);
    assert(ring.total() == 10000 && ring.retained() == 4);
    assert(ring.overwritten() == 9996 && ring.firstNumber() == 9997);
    assert(ring.count(EventType::PixSof) == 10000);
    for (unsigned int i = 0; i < 4; ++i) {
        assert(ring.at(i).number == i+9997);
        assert(ring.at(i).sof == i+9997);
        assert(ring.at(i).hardwareNs == uint64_t(i+9997)*33333333);
    }
    event.type = uint16_t(EventType::Count);
    ring.push(event); assert(ring.total() == 10000);
    for (unsigned int cycle = 0; cycle < 4; ++cycle) {
        assert(ring.prepare()); assert(ring.total() == 0);
        event.type = uint16_t(EventType::FullDq); event.status = 0;
        ring.push(event);
        assert(ring.underflows() == 1 && ring.at(0).outstandingFull == 0);
        event.type = uint16_t(EventType::FullQbufResult); event.status = -EIO;
        ring.push(event); assert(ring.at(1).outstandingFull == 0);
        event.status = 0; ring.push(event);
        assert(ring.at(2).outstandingFull == 1);
        event.type = uint16_t(EventType::FullDq);
        ring.push(event); assert(ring.at(3).outstandingFull == 0);
        ring.reset(); assert(!ring.active() && ring.total() == 0);
    }
    Capture capture;
    before = allocations;
    assert(capture.start(nullptr, 1) == 0);
    capture.record(event); assert(capture.stop() == 0);
    if(capture.active() || allocations != before)
        std::fprintf(stderr,"disabled active=%d allocations=%llu before=%llu\n",
                     capture.active(),(unsigned long long)allocations.load(),(unsigned long long)before);
    assert(!capture.active() && allocations == before);
    assert(capture.start("/definitely-absent-k452-directory", 1) < 0);
    assert(!capture.active());
    failNothrow = true;
    assert(capture.start(argv[1], 4) == -ENOMEM && !capture.active());

    assert(capture.start(argv[1], 5) == 0 && capture.active());
    const std::string filename = capture.filename();
    before = allocations;
    event.type = uint16_t(EventType::PixSof);
    for (unsigned int i = 1; i <= 9000; ++i) {
        event.sof=i; event.hardwareNs=uint64_t(i)*33273000;
        event.requestSequence=Unknown; event.lastSof=i-1;
        capture.record(event);
    }
    assert(allocations == before);
    assert(capture.stop() == 0 && !capture.active());
    assert(capture.stop() == 0);
    assert(capture.lastTotal() == 9000 && capture.lastRetained() == 8192 &&
           capture.lastOverwritten() == 808);
    const std::string path = std::string(argv[1])+"/"+filename;
    struct stat statbuf{};
    assert(stat(path.c_str(), &statbuf) == 0 && (statbuf.st_mode & 0777) == 0600);

    assert(capture.start(argv[1], 6) == 0);
    const std::string collision = std::string(argv[1])+"/"+capture.filename();
    const int fd = open(collision.c_str(), O_WRONLY|O_CREAT|O_EXCL, 0600);
    assert(fd >= 0);
    assert(write(fd, "sentinel", 8) == 8); close(fd);
    capture.record(event);
    assert(capture.stop() == -EEXIST && !capture.active());
    assert(capture.stop() == 0);
    char contents[16]{};
    const int check = open(collision.c_str(), O_RDONLY);
    assert(check >= 0 && read(check, contents, sizeof contents) == 8);
    close(check); assert(std::strcmp(contents, "sentinel") == 0);
    std::printf("{\"passed\":true,\"ring_wrap_events\":10000,\"cycles\":4,"
                "\"hot_path_new_calls\":0,\"capture_events\":9000,"
                "\"retained\":8192,\"overwritten\":808,\"csv\":\"%s\"}\n",
                filename.c_str());
}
