#!/usr/bin/env python3
"""Refresh HANDOVER-NEXT.md (2026-10-08): current repo state, the real open
questions, file references in place of the old section numbers.

Idempotent: every block is skipped if it is already there.
"""
import sys

W = "/mnt/e/RealmeX2Pro edk2"
P = W + "/HANDOVER-NEXT.md"
bq = chr(96)
t = open(P, encoding="utf-8").read()
before = t

def sub(old, new, what):
    global t
    n = t.count(old)
    if n == 0:
        print("  MISS   " + what)
        return
    t = t.replace(old, new)
    print("  ok     %-24s (%d)" % (what, n))

def block(start, end, new, what):
    global t
    i = t.find(start)
    j = t.find(end, i)
    if i < 0 or j < 0:
        print("  MISS   " + what)
        return
    t = t[:i] + new + t[j:]
    print("  ok     " + what)

# 1. old section numbers -> file references
sub("(section 29.1)", "(" + bq + "sessions/29-eud-console-tty-command-channel.md" + bq + ", 29.1)", "ref 29.1")
sub("(section 29.5)", "(" + bq + "sessions/29-eud-console-tty-command-channel.md" + bq + ", 29.5)", "ref 29.5")
sub("(sections 28.4 and 28.6)", "(" + bq + "sessions/28-flywheel.md" + bq + ", 28.4/28.6)", "ref 28.4/28.6")
sub("in section 27.4 goal 2", "in " + bq + "sessions/27-userspace-and-shortcuts.md" + bq + ", 27.4 goal 2", "ref 27.4")

# 2. section 3 - current repository state
new3 = (
"## 3. Repo state\n"
"\n"
"    master = 721d2f2  docs: drop the stale DIAG-CAPTURE.md from the mirror\n"
"             15f7303  docs: split EUD.md and DIAG-CAPTURE.md into single-topic files\n"
"             7ccb70e  samurai: track the disabled boot-layout include\n"
"             f201abf  linux-port: NN-<topic> doc names, an index, guards\n"
"             2789b41  docs: split the 109 KB handover into a slim entry + sections\n"
"             2d0e68e  docs: index the documentation; the two 2026-10-06 records\n"
"             2e64714  linux-port: the real-console driver and the 0003 patch\n"
"             9923607  gitignore: keep the built kernel Image out of the tree\n"
"             7b9dc82  docs: EUD COM is a real console now (sections 29-30)\n"
"\n"
"    fork remote: https://github.com/hmhmdcy/edk2-realme-x2-pro\n"
"                 push with:  git push fork master\n"
"                 (a plain git push goes to upstream edk2-porting/edk2-msm - never do that)\n"
"    Roughly 50 commits ahead of upstream origin/master; all of them are on the fork.\n"
"\n"
"Documentation layout (2026-10-08; the full map is DOCS-INDEX.md):\n"
"    HANDOVER-NEXT.md               this file: sections 0-7 + the history index\n"
"    DOCS-INDEX.md                  documentation map, sync commands, maintenance rules\n"
"    reference/DECISIONS.md         former sections 8-11\n"
"    sessions/NN-<topic>.md         former sections 12-18, 29, 30 (+ two 2026-10-06 records)\n"
"    linux-port/docs/NN-<topic>.md  former sections 19-28, see its 00-INDEX.md\n"
"    archive/HANDOVER-NEXT-full-2026-10-08.md   the pre-split text, verbatim\n"
"    EUD.md, SWD-JTAG.md, RX-CONSOLE.md, BINARIES.md, README.md\n"
"\n"
"Editing happens in E:\\RealmeX2Pro edk2 (Windows); publish with:\n"
"    linux-port/scripts/sync-docs-to-repo.sh    top-level docs + health check + push\n"
"    linux-port/scripts/mirror-linux-port.sh    the linux-port/ mirror\n"
"docs-health-check.sh must print RESULT: clean before anything is pushed.\n"
"\n"
"SerialPortLib scoping in samurai.dsc (important, do not widen casually):\n"
"    DXE_DRIVER / DXE_RUNTIME_DRIVER / UEFI_DRIVER / UEFI_APPLICATION -> EudSerialPortLib\n"
"    PrePI / PEI / SEC and DXE_CORE keep FrameBufferSerialPortLib\n"
"\n"
"The per-commit detail that used to be listed here (EudSerialPortLib, the samurai.dsc\n"
"overrides, PlatformBm.c, EUD.md) is in git log and in sessions/15-17.\n"
"\n"
"\n")
if "master = 721d2f2" in t:
    print("  skip   section 3 (already refreshed)")
else:
    block("## 3. Repo state\n", "## 4. Tools and paths", new3, "section 3 refreshed")

# 3. section 5, item 3 - the stale "Fix = Step 2 or Step 3" line
sub("   Keep PcdDebugPrintErrorLevel at the platform default (0x80000000) and do\n"
    "   not override SerialPortLib for DXE_CORE.  Fix = Step 2 or Step 3 above.\n",
    "   Keep PcdDebugPrintErrorLevel at the platform default (0x80000000) and do\n"
    "   not override SerialPortLib for DXE_CORE.  The root cause and the real fix\n"
    "   (no DEBUG print in the ArmMmuLib MMU-off path) are in sessions/15.\n",
    "section 5 item 3")

# 4. section 7 - only genuinely open questions
new7 = (
"## 7. Open questions\n"
"\n"
"* Can the log channel survive the UEFI -> OS handoff (useful for Linux boot\n"
"  debugging), and what does the Android kernel ttyEUD see at that point?\n"
"* The RX payload read stays dangerous until step 2 of section 1 lands: 0x14 may\n"
"  only be read exactly len times, once the header latch has changed, or the EUD\n"
"  block wedges until a full power cycle (sessions/29-..., 29.5).\n"
"\n"
"Answered since; kept here so nobody re-opens them:\n"
"\n"
"* EUD COM drain speed with full DEBUG on: fine now - paced writes, and a 210 s\n"
"  capture reassembles with 0 resyncs (sessions/15, sessions/16).\n"
"* Why EUD SWD 9504 did not enumerate after CTLOUT_SET 0x645 + attach: the\n"
"  transport works, the AP DAP is unreachable on this retail unit (APPS_DBGEN_DISABLE\n"
"  fuse + signed APDP debug policy) - see SWD-JTAG.md and Mnemon document 06827d0c.\n"
"\n")
if "Answered since; kept here" not in t:
    block("## 7. Open questions\n", "\n---\n", new7, "section 7 refreshed")

if t == before:
    print("nothing changed")
else:
    open(P, "w", encoding="utf-8", newline="\n").write(t)
    print("written: %d -> %d bytes" % (len(before.encode()), len(t.encode())))