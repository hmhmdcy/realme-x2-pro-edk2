/* comlog2 - EUD COM logger with resync and a raw dump.
 *
 * The target writes frames of [0x90][LEN][DATA...] through the EUD COM FIFO.
 * If the FIFO overflows a byte is lost, the frame boundary slips and the old
 * parser silently mis-framed the rest of the capture, which is why the logs
 * came out as interleaved fragments.  This one:
 *   - never writes anything to the port (the old one sent 10 bytes at start),
 *   - resynchronises aggressively and reports how often it had to,
 *   - keeps the untouched byte stream in <log>.raw so the real framing can be
 *     inspected offline,
 *   - reads continuously instead of once every 50 ms.
 *
 * build: g++ -O2 -o comlog2.exe comlog2.cpp
 * use:   comlog2.exe COM14 600 E:\eud-host\out.log
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <windows.h>

#define MAXLEN 64

static void ts(char *b, size_t n) {
    SYSTEMTIME st; GetLocalTime(&st);
    sprintf_s(b, n, "[%02d:%02d:%02d.%03d]", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *port    = (argc > 1) ? argv[1] : "COM14";
    int         seconds = (argc > 2) ? atoi(argv[2]) : 600;
    const char *logfile = (argc > 3) ? argv[3] : "E:\\eud-host\\eud-com.log";

    char path[64];
    sprintf_s(path, sizeof(path), "\\\\.\\%s", port);
    HANDLE h = CreateFileA(path, GENERIC_READ, 0, NULL, OPEN_EXISTING, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) { printf("open %s failed err=%lu\n", path, GetLastError()); return 1; }

    COMMTIMEOUTS to; memset(&to, 0, sizeof(to));
    to.ReadIntervalTimeout = MAXDWORD;     /* return immediately with what is there */
    SetCommTimeouts(h, &to);

    FILE *f = fopen(logfile, "wb");        /* text log, rewritten */
    char rawpath[512];
    sprintf_s(rawpath, sizeof(rawpath), "%s.raw", logfile);
    FILE *fr = fopen(rawpath, "wb");       /* untouched bytes */
    if (!f) { printf("cannot open %s\n", logfile); return 1; }
    printf("logging %s -> %s (+ .raw) for %d s\n", path, logfile, seconds);

    char tb[32];
    char line[2048]; int  linelen = 0;
    unsigned char frame[MAXLEN]; unsigned framelen = 0, got = 0;
    int state = 0;                          /* 0 hunt, 1 want len, 2 data */
    unsigned long bytes = 0, frames = 0, resync = 0, badlen = 0;
    DWORD start = GetTickCount();

    while ((GetTickCount() - start) < (DWORD)seconds * 1000) {
        unsigned char buf[4096];
        DWORD r = 0;
        if (!ReadFile(h, buf, sizeof(buf), &r, NULL) || r == 0) { Sleep(5); continue; }
        bytes += r;
        if (fr) fwrite(buf, 1, r, fr);

        for (DWORD k = 0; k < r; k++) {
            unsigned char c = buf[k];
            switch (state) {
            case 0:
                if (c == 0x90) state = 1;
                break;
            case 1:
                if (c == 0 || c > MAXLEN) {         /* not a length: resync on this byte */
                    badlen++;
                    state = (c == 0x90) ? 1 : 0;
                    break;
                }
                framelen = c; got = 0; state = 2;
                break;
            default:
                frame[got++] = c;
                if (got < framelen) break;
                frames++;
                for (unsigned q = 0; q < framelen; q++) {
                    char ch = (char)frame[q];
                    if (ch == '\n' || ch == '\r') {
                        if (linelen > 0) {
                            line[linelen] = 0; ts(tb, sizeof(tb));
                            printf("%s %s\n", tb, line);
                            fprintf(f, "%s %s\n", tb, line); fflush(f);
                            linelen = 0;
                        }
                    } else if (linelen < (int)sizeof(line) - 1) {
                        line[linelen++] = ch;
                    }
                }
                state = 0;
                break;
            }
        }
    }

    if (linelen > 0) { line[linelen] = 0; ts(tb, sizeof(tb)); printf("%s %s\n", tb, line); fprintf(f, "%s %s\n", tb, line); }
    printf("--- %lu raw bytes, %lu frames, %lu bad-length resyncs ---\n", bytes, frames, badlen);
    printf("--- raw stream kept in %s ---\n", rawpath);
    fclose(f); if (fr) fclose(fr); CloseHandle(h);
    (void)resync;
    return 0;
}