#!/usr/bin/env python3
"""P1 (2026-10-08): split EUD.md and DIAG-CAPTURE.md into single-topic files.

  EUD.md          -> EUD.md (core) + SWD-JTAG.md + RX-CONSOLE.md
  DIAG-CAPTURE.md -> sessions/2026-10-06-diagvendor-capture.md
                     sessions/2026-10-06-eud-first-test.md   (then the file is dropped)

DIAG-CAPTURE.md has two documents but three level-1 headings (the first document
has a later result heading), so the split point is the heading that starts with
"# EUD" - the second document.
Idempotent.
"""
import os

W = "/mnt/e/RealmeX2Pro edk2"
EUD = os.path.join(W, "EUD.md")
DIAG = os.path.join(W, "DIAG-CAPTURE.md")
SESS = os.path.join(W, "sessions")
SCRIPTS = os.path.join(W, "linux-port", "scripts")
STAMP = "2026-10-08"

OLD_LIST = "DIAG-CAPTURE.md"
NEW_FILES = "SWD-JTAG.md RX-CONSOLE.md"

def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def write(p, t):
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    print("  wrote %-46s %6d bytes" % (os.path.relpath(p, W), len(t.encode())))

def split_eud():
    if os.path.exists(os.path.join(W, "SWD-JTAG.md")):
        print("== EUD.md: already split, skipping")
        return
    lines = read(EUD).splitlines(keepends=True)
    i_swd = i_rx = None
    for i, l in enumerate(lines):
        if l.startswith("## SWD / JTAG") and i_swd is None:
            i_swd = i
        if l.startswith("## RX side:") and i_rx is None:
            i_rx = i
    if i_swd is None or i_rx is None or i_rx <= i_swd:
        raise SystemExit("EUD.md: cannot find the two split headings (swd=%s rx=%s)" % (i_swd, i_rx))
    print("== EUD.md: split at lines %d (SWD) and %d (RX)" % (i_swd + 1, i_rx + 1))
    note = ("\n## Where the rest went (split 2026-10-08)\n\n"
            "The two hardware-verification topics that used to be the tail of this file now\n"
            "live on their own: SWD-JTAG.md (EUD SWD 9504 / JTAG 9503 - the transport works,\n"
            "the AP DAP is unreachable on this retail unit) and RX-CONSOLE.md (RX registers\n"
            "0x0c/0x10/0x14, framing, the tty driver and the 0x14 wedge).  Everything above\n"
            "stays here: device facts, registers, CTL/COM protocol, host tools, the firmware\n"
            "log ring, the ArmMmuLib crash and the full-DEBUG story.\n")
    write(EUD, "".join(lines[:i_swd]).rstrip() + "\n" + note)
    hdr = ("# EUD SWD / JTAG on the realme X2 Pro\n\n"
           "> Split out of EUD.md on %s; verbatim from there.  EUD COM (the console) is in\n"
           "> EUD.md and RX-CONSOLE.md.\n\n---\n\n" % STAMP)
    write(os.path.join(W, "SWD-JTAG.md"), hdr + "".join(lines[i_swd:i_rx]).rstrip() + "\n")
    hdr = ("# EUD RX side: registers, framing and the console driver\n\n"
           "> Split out of EUD.md on %s; verbatim from there.  The TX side and the firmware\n"
           "> log ring are in EUD.md.\n\n---\n\n" % STAMP)
    write(os.path.join(W, "RX-CONSOLE.md"), hdr + "".join(lines[i_rx:]).rstrip() + "\n")

def split_diag():
    if not os.path.exists(DIAG):
        print("== DIAG-CAPTURE.md: gone already, skipping")
        return
    lines = read(DIAG).splitlines(keepends=True)
    marks = [i for i, l in enumerate(lines) if l.startswith("# ")]
    b = None
    for i in marks:
        if lines[i].startswith("# EUD"):
            b = i
            break
    print("== DIAG-CAPTURE.md: level-1 headings at %s; second document starts at %s"
          % ([m + 1 for m in marks], (b + 1) if b is not None else "?"))
    if b is None or b == 0:
        raise SystemExit("DIAG-CAPTURE.md: cannot find the second document (# EUD ...)")
    os.makedirs(SESS, exist_ok=True)
    write(os.path.join(SESS, "2026-10-06-diagvendor-capture.md"),
          "<!-- split out of DIAG-CAPTURE.md on %s (document 1 of 2), verbatim -->\n\n" % STAMP
          + "".join(lines[:b]).rstrip() + "\n")
    write(os.path.join(SESS, "2026-10-06-eud-first-test.md"),
          "<!-- split out of DIAG-CAPTURE.md on %s (document 2 of 2), verbatim -->\n\n" % STAMP
          + "".join(lines[b:]).rstrip() + "\n")
    os.remove(DIAG)
    print("  removed DIAG-CAPTURE.md")

def refresh_lists():
    for name in ("docs-health-check.sh", "sync-docs-to-repo.sh"):
        p = os.path.join(SCRIPTS, name)
        if not os.path.isfile(p):
            continue
        t = read(p)
        n = t.replace(OLD_LIST, NEW_FILES)
        if n != t:
            write(p, n)
            print("  %s: file list refreshed" % name)

def fix_readme():
    p = os.path.join(W, "README.md")
    t = read(p)
    n = t.replace("Details in EUD.md.", "Details in RX-CONSOLE.md.")
    if n != t:
        write(p, n)
        print("  README.md: RX pointer now says RX-CONSOLE.md")

print("== split EUD.md ==")
split_eud()
print("== split DIAG-CAPTURE.md ==")
split_diag()
print("== refresh the script file lists ==")
refresh_lists()
print("== fix the README pointer ==")
fix_readme()
print("done")