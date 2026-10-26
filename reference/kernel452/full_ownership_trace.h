/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once

#include <array>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <fcntl.h>
#include <memory>
#include <new>
#include <time.h>
#include <unistd.h>

namespace libcamera::camss_diag {

enum class EventType : uint16_t {
    Start, PoolReady, RequestEnter, NoFreeFull, InternalTake, FullQbufBegin,
    FullQbufResult, FullDq, PixSof, Pd10Dq, StatsDq, StatsDone, WaitOlder,
    WaitIpe, WaitPd10, IpeClaim, IpeQueue, ImageProcessed, InternalReturn,
    RequestComplete, RequestAccepted, StopBegin, StopEnd, Count
};
constexpr uint32_t Unknown = UINT32_MAX;
enum Flags : uint32_t {
    Running = 1, IpeActive = 2, ParameterBusy = 4,
    BufferSuccess = 8, BufferTimestampMonotonic = 16
};
struct Event {
    uint64_t number, monoNs, epoch, request, buffer, hardwareNs, activeRequest;
    uint32_t sof, requestSequence, lastSof;
    uint32_t freeFull, requests, waitingFull, coarse, histograms, statistics, associations, flags;
    int32_t status, outstandingFull;
    uint16_t type, reserved;
};
static_assert(sizeof(Event) == 112);

/* Single CameraManager thread only. Nested IPC dispatch is sequential; push()
 * finishes before any call-out. No callbacks, allocation or I/O inside push(). */
template<size_t Capacity>
class Ring
{
    static_assert(Capacity > 0);
public:
    bool prepare()
    {
        reset();
        events_.reset(new (std::nothrow) Event[Capacity]);
        if (!events_)
            return false;
        /* calloc/value-init can leave demand-zero pages untouched. */
        volatile unsigned char *bytes =
            reinterpret_cast<volatile unsigned char *>(events_.get());
        for (size_t i = 0; i < sizeof(Event) * Capacity; i += 4096)
            bytes[i] = 0;
        bytes[sizeof(Event) * Capacity - 1] = 0;
        return true;
    }
    bool active() const { return bool(events_); }
    void push(Event event)
    {
        if (!active())
            return;
        const auto kind = EventType(event.type);
        if (kind >= EventType::Count)
            return;
        ++totals_[event.type];
        if (kind == EventType::FullQbufResult && !event.status)
            ++outstanding_;
        if (kind == EventType::FullDq) {
            if (outstanding_ > 0)
                --outstanding_;
            else
                ++underflows_;
        }
        event.number = ++total_;
        event.outstandingFull = outstanding_;
        events_[(total_ - 1) % Capacity] = event;
    }
    size_t retained() const { return total_ < Capacity ? total_ : Capacity; }
    uint64_t total() const { return total_; }
    uint64_t overwritten() const { return total_ - retained(); }
    uint64_t firstNumber() const { return total_ ? total_ - retained() + 1 : 0; }
    uint64_t underflows() const { return underflows_; }
    uint64_t count(EventType type) const { return totals_[uint16_t(type)]; }
    const Event &at(size_t chronologicalIndex) const
    {
        return events_[(firstNumber() - 1 + chronologicalIndex) % Capacity];
    }
    void reset()
    {
        events_.reset();
        total_ = 0; outstanding_ = 0; underflows_ = 0; totals_.fill(0);
    }
private:
    std::unique_ptr<Event[]> events_;
    std::array<uint64_t, size_t(EventType::Count)> totals_{};
    uint64_t total_ = 0, underflows_ = 0;
    int32_t outstanding_ = 0;
};

class Capture
{
public:
    static constexpr size_t Capacity = 8192;
    ~Capture() { reset(); }
    int start(const char *directory, uint64_t epoch)
    {
        reset(); lastTotal_ = lastRetained_ = lastOverwritten_ = 0;
        if (!directory || !*directory)
            return 0;
        directory_ = open(directory, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
        if (directory_ < 0)
            return -errno;
        if (!ring_.prepare()) {
            reset();
            return -ENOMEM;
        }
        epoch_ = epoch;
        std::snprintf(filename_, sizeof filename_, "full-%ld-e%llu-%llu.csv",
                      long(getpid()), (unsigned long long)epoch,
                      (unsigned long long)now());
        return 0;
    }
    bool active() const { return directory_ >= 0 && ring_.active(); }
    void record(Event event)
    {
        if (!active())
            return;
        event.monoNs = now();
        event.epoch = epoch_;
        ring_.push(event);
    }
    const char *filename() const { return filename_; }
    uint64_t lastTotal() const { return lastTotal_; }
    uint64_t lastRetained() const { return lastRetained_; }
    uint64_t lastOverwritten() const { return lastOverwritten_; }
    int stop()
    {
        if (!active())
            return 0;
        lastTotal_ = ring_.total(); lastRetained_ = ring_.retained();
        lastOverwritten_ = ring_.overwritten();
        const int fd = openat(directory_, filename_,
                              O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
        if (fd < 0) {
            const int error = -errno; reset(); return error;
        }
        FILE *file = fdopen(fd, "w");
        if (!file) {
            const int error = -errno; close(fd); reset(); return error;
        }
        std::fprintf(file, "# full-trace,version=1,capacity=%zu,total=%llu,retained=%llu,overwritten=%llu,first=%llu,clock-errors=%llu,q-underflows=%llu\n",
                     Capacity, (unsigned long long)ring_.total(),
                     (unsigned long long)ring_.retained(), (unsigned long long)ring_.overwritten(),
                     (unsigned long long)ring_.firstNumber(), (unsigned long long)clockErrors_,
                     (unsigned long long)ring_.underflows());
        for (uint16_t i = 0; i < uint16_t(EventType::Count); ++i)
            std::fprintf(file, "# total,%u,%llu\n", i, (unsigned long long)ring_.count(EventType(i)));
        std::fprintf(file, "number,mono_ns,epoch,request,buffer,hardware_ns,active_request,type,sof,request_sequence,last_sof,free_full,requests,waiting_full,coarse,histograms,statistics,associations,flags,status,outstanding_full\n");
        for (size_t i = 0; i < ring_.retained(); ++i) {
            const Event &e = ring_.at(i);
            const uint64_t values[] = {
                e.number, e.monoNs, e.epoch, e.request, e.buffer, e.hardwareNs, e.activeRequest,
                e.type, e.sof, e.requestSequence, e.lastSof, e.freeFull, e.requests,
                e.waitingFull, e.coarse, e.histograms, e.statistics, e.associations, e.flags
            };
            for (uint64_t value : values)
                std::fprintf(file, "%llu,", (unsigned long long)value);
            std::fprintf(file, "%d,%d\n", e.status, e.outstandingFull);
        }
        std::fprintf(file, "# end,records=%llu\n", (unsigned long long)ring_.retained());
        int result = std::ferror(file) ? -EIO : 0;
        if (std::fclose(file) && !result)
            result = -errno;
        reset();
        return result;
    }
private:
    uint64_t now()
    {
        timespec value{};
        if (clock_gettime(CLOCK_MONOTONIC, &value)) {
            ++clockErrors_;
            return 0;
        }
        return uint64_t(value.tv_sec) * 1000000000 + value.tv_nsec;
    }
    void reset()
    {
        if (directory_ >= 0)
            close(directory_);
        directory_ = -1;
        ring_.reset(); epoch_ = 0; clockErrors_ = 0;
    }
    Ring<Capacity> ring_;
    int directory_ = -1;
    uint64_t epoch_ = 0, clockErrors_ = 0;
    uint64_t lastTotal_ = 0, lastRetained_ = 0, lastOverwritten_ = 0;
    char filename_[96]{};
};

} /* namespace libcamera::camss_diag */
