#!/usr/bin/env python3
"""Boot the kernel straight from PlatformBootManagerAfterConsole.

SimpleInit is the configured boot manager on this handset, but its default
entry (Android from the boot partition, which now holds this firmware) fails
and SimpleInit resets the phone about eight seconds later, so its GUI only ever
loops.  Starting the kernel here sidesteps the boot order completely and keeps
the EUD log channel, which is enabled a few lines above.
"""
import os, sys

RK = "/home/cy122/edk2-samurai/repo"
p = os.path.join(RK, "Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c")
s = open(p, encoding="utf-8").read()


def sub(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit("anchor found %d times (want 1):\n%r" % (n, old[:200]))
    s = s.replace(old, new, 1)


# 1. the scanner boots what it found
sub(
    "    if (OptionIndex == -1) {\n"
    "      EfiBootManagerAddLoadOptionVariable (&NewOption, MAX_UINTN);\n"
    "      Print (L\"[SAMURAI] kernel found, registered \\\"Linux (mainline samurai)\\\"\\n\");\n"
    "    } else {\n"
    "      Print (L\"[SAMURAI] kernel boot option is already present\\n\");\n"
    "    }\n",

    "    if (OptionIndex == -1) {\n"
    "      EfiBootManagerAddLoadOptionVariable (&NewOption, MAX_UINTN);\n"
    "      Print (L\"[SAMURAI] kernel found, registered \\\"Linux (mainline samurai)\\\"\\n\");\n"
    "    } else {\n"
    "      Print (L\"[SAMURAI] kernel boot option is already present\\n\");\n"
    "    }\n"
    "\n"
    "    //\n"
    "    // SAMURAI: start it right now.  SimpleInit is the configured boot manager on this\n"
    "    // handset and its default entry fails (it points at the boot partition, which holds\n"
    "    // this firmware), after which it resets the phone about eight seconds later - so its\n"
    "    // GUI only ever loops and nothing can be selected in time.  Booting here skips the\n"
    "    // boot order altogether and is what bring-up wants anyway.  Comment the next two\n"
    "    // lines out to get the boot menu back.\n"
    "    //\n"
    "    Print (L\"[SAMURAI] starting \\\\Image now\\n\");\n"
    "    EfiBootManagerBoot (&NewOption);\n"
    "    Print (L\"[SAMURAI] EfiBootManagerBoot returned - the kernel did not take over\\n\");\n")

# 2. move the registration to the very end, after EUD is up
sub("  //\n"
    "  // SAMURAI: find the mainline Linux kernel on a file system and register it.  BDS\n"
    "  // has already enabled EUD before the console is set up, so a host PC that ran\n"
    "  // \"eudtool com-up\" on the boot menu gets the complete kernel log from earlycon.\n"
    "  //\n"
    "  SamuraiRegisterKernelBootOption ();\n", "")

sub("    DEBUG ((DEBUG_ERROR, \"[SAMURAI-EUD-COM] SerialPortLib ready\\n\"));\n"
    "#endif\n"
    "\n"
    "  PlatformSetup();\n"
    "}\n",

    "    DEBUG ((DEBUG_ERROR, \"[SAMURAI-EUD-COM] SerialPortLib ready\\n\"));\n"
    "#endif\n"
    "\n"
    "  PlatformSetup();\n"
    "\n"
    "#ifdef SAMURAI_LINUX_KERNEL\n"
    "  //\n"
    "  // SAMURAI: find the mainline Linux kernel on a file system, register it and start it.\n"
    "  // Kept last on purpose: EUD is enabled above, so the complete earlycon log of the\n"
    "  // kernel reaches a host PC that already ran \"eudtool com-up\".\n"
    "  //\n"
    "  SamuraiRegisterKernelBootOption ();\n"
    "#endif\n"
    "}\n")

open(p, "w", encoding="utf-8").write(s)
print("patched", p)