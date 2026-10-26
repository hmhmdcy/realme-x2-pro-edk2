// Local single-device installer preparation. Audit does not stage or bind a driver.
using System;
using System.ComponentModel;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace Rx63 {
  public sealed class DriverRecord {
    public string Description, Provider, InfPath, Section, HardwareIds, Version, DateUtc;
  }
  public sealed class BindingResult { public string PublishedInf; public bool NeedReboot; }
  public static class DeviceDriver {
    public static int StageCalls, InstallCalls;
    static readonly Guid Ports = new Guid("4d36e978-e325-11ce-bfc1-08002be10318");
    const uint CompatibleDriver = 2;
    [StructLayout(LayoutKind.Sequential)] struct DevInfo {
      public uint cbSize; public Guid ClassGuid; public uint DevInst; public UIntPtr Reserved;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct InstallParams {
      public uint cbSize, Flags, FlagsEx;
      public IntPtr hwndParent, InstallMsgHandler, InstallMsgHandlerContext, FileQueue;
      public UIntPtr ClassInstallReserved; public uint Reserved;
      [MarshalAs(UnmanagedType.ByValTStr, SizeConst=260)] public string DriverPath;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct DriverInfo {
      public uint cbSize, DriverType; public UIntPtr Reserved;
      [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string Description;
      [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string MfgName;
      [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string ProviderName;
      public System.Runtime.InteropServices.ComTypes.FILETIME DriverDate; public ulong DriverVersion;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct DriverDetail {
      public uint cbSize; public System.Runtime.InteropServices.ComTypes.FILETIME InfDate;
      public uint CompatIDsOffset, CompatIDsLength; public UIntPtr Reserved;
      [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string SectionName;
      [MarshalAs(UnmanagedType.ByValTStr, SizeConst=260)] public string InfFileName;
      [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string DrvDescription;
      [MarshalAs(UnmanagedType.ByValTStr, SizeConst=1)] public string HardwareID;
    }
    [StructLayout(LayoutKind.Sequential)] struct CodeIntegrity { public uint Length, Options; }
    [DllImport("ntdll.dll")] static extern int NtQuerySystemInformation(int kind, ref CodeIntegrity info, uint length, out uint returned);
    [DllImport("setupapi.dll", SetLastError=true)] static extern IntPtr SetupDiCreateDeviceInfoList(IntPtr cls, IntPtr parent);
    [DllImport("setupapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupDiOpenDeviceInfoW(IntPtr set, string id, IntPtr parent, uint flags, ref DevInfo device);
    [DllImport("setupapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupDiGetDeviceInstallParamsW(IntPtr set, ref DevInfo device, ref InstallParams parameters);
    [DllImport("setupapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupDiSetDeviceInstallParamsW(IntPtr set, ref DevInfo device, ref InstallParams parameters);
    [DllImport("setupapi.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupDiBuildDriverInfoList(IntPtr set, ref DevInfo device, uint type);
    [DllImport("setupapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupDiEnumDriverInfoW(IntPtr set, ref DevInfo device, uint type, uint index, ref DriverInfo driver);
    [DllImport("setupapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupDiGetDriverInfoDetailW(IntPtr set, ref DevInfo device, ref DriverInfo driver, IntPtr detail, uint size, out uint required);
    [DllImport("setupapi.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupDiDestroyDriverInfoList(IntPtr set, ref DevInfo device, uint type);
    [DllImport("setupapi.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupDiDestroyDeviceInfoList(IntPtr set);
    [DllImport("setupapi.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool SetupCopyOEMInfW(string source, string media, uint mediaType, uint style, StringBuilder destination, uint size, out uint required, IntPtr component);
    [DllImport("newdev.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)] static extern bool DiInstallDevice(IntPtr parent, IntPtr set, ref DevInfo device, ref DriverInfo driver, uint flags, [MarshalAs(UnmanagedType.Bool)] out bool reboot);
    static void Check(bool success, string operation) {
      if (!success) throw new Win32Exception(Marshal.GetLastWin32Error(), operation);
    }
    public static uint CurrentCodeIntegrity() {
      var info = new CodeIntegrity { Length=8 }; uint returned;
      int status = NtQuerySystemInformation(103, ref info, 8, out returned);
      if (status != 0 || returned != 8 || info.Length != 8)
        throw new InvalidOperationException("Code Integrity query unavailable; refuse to infer test-signing state. NTSTATUS="+status.ToString("x8"));
      return info.Options;
    }
    public static int[] StructureSizes() {
      return new [] { Marshal.SizeOf(typeof(DevInfo)), Marshal.SizeOf(typeof(InstallParams)), Marshal.SizeOf(typeof(DriverInfo)), Marshal.SizeOf(typeof(DriverDetail)) };
    }
    static DriverRecord Detail(IntPtr set, ref DevInfo dev, ref DriverInfo driver) {
      uint required;
      bool first = SetupDiGetDriverInfoDetailW(set, ref dev, ref driver, IntPtr.Zero, 0, out required);
      int error = Marshal.GetLastWin32Error();
      if (first || error != 122 || required < 1578 || required > 65536)
        throw new InvalidOperationException("Unexpected driver detail size/error: "+required+"/"+error);
      uint size = Math.Max(required, (uint)Marshal.SizeOf(typeof(DriverDetail)));
      IntPtr memory = Marshal.AllocHGlobal((int)size);
      try {
        for (int i=0; i<(int)size; i++) Marshal.WriteByte(memory, i, 0);
        Marshal.WriteInt32(memory, Marshal.SizeOf(typeof(DriverDetail)));
        Check(SetupDiGetDriverInfoDetailW(set, ref dev, ref driver, memory, size, out required), "Driver detail");
        var detail = (DriverDetail)Marshal.PtrToStructure(memory, typeof(DriverDetail));
        int idOffset = (int)Marshal.OffsetOf(typeof(DriverDetail), "HardwareID");
        string ids = Marshal.PtrToStringUni(IntPtr.Add(memory,idOffset), ((int)required-idOffset)/2).TrimEnd('\0').Replace('\0','|');
        long date = ((long)driver.DriverDate.dwHighDateTime << 32) | (uint)driver.DriverDate.dwLowDateTime;
        ulong v = driver.DriverVersion;
        return new DriverRecord { Description=driver.Description, Provider=driver.ProviderName,
          InfPath=detail.InfFileName, Section=detail.SectionName, HardwareIds=ids,
          Version=(v>>48)+"."+((v>>32)&65535)+"."+((v>>16)&65535)+"."+(v&65535),
          DateUtc=DateTime.FromFileTimeUtc(date).ToString("o") };
      } finally { Marshal.FreeHGlobal(memory); }
    }
    // List settings are confined to this transient device-info handle.
    static DriverRecord Select(string id, string inf, bool install, out bool reboot) {
      if (IntPtr.Size != 8 || !id.StartsWith("USB\\VID_05C6&PID_9505\\", StringComparison.OrdinalIgnoreCase))
        throw new InvalidOperationException("Only a single explicit EUD 9505 instance in a 64-bit process is supported.");
      inf = Path.GetFullPath(inf);
      if (!File.Exists(inf) || inf.Length >= 260) throw new InvalidOperationException("INF unavailable/path too long.");
      IntPtr set = SetupDiCreateDeviceInfoList(IntPtr.Zero, IntPtr.Zero);
      if (set == new IntPtr(-1)) throw new Win32Exception(Marshal.GetLastWin32Error());
      var dev = new DevInfo { cbSize=(uint)Marshal.SizeOf(typeof(DevInfo)) };
      bool built=false; reboot=false;
      try {
        Check(SetupDiOpenDeviceInfoW(set,id,IntPtr.Zero,0,ref dev),"Open exact device-info element");
        if (dev.ClassGuid != Ports) throw new InvalidOperationException("Target is not the Ports class.");
        var parameters = new InstallParams { cbSize=(uint)Marshal.SizeOf(typeof(InstallParams)) };
        Check(SetupDiGetDeviceInstallParamsW(set,ref dev,ref parameters),"Get transient list parameters");
        parameters.Flags |= 0x00010000; // DI_ENUMSINGLEINF
        parameters.FlagsEx |= 0x00000800; // DI_FLAGSEX_ALLOWEXCLUDEDDRVS
        parameters.DriverPath=inf;
        Check(SetupDiSetDeviceInstallParamsW(set,ref dev,ref parameters),"Set exact INF search");
        Check(SetupDiBuildDriverInfoList(set,ref dev,CompatibleDriver),"Build compatible list for exact device/INF");
        built=true;
        var driver = new DriverInfo { cbSize=(uint)Marshal.SizeOf(typeof(DriverInfo)) };
        Check(SetupDiEnumDriverInfoW(set,ref dev,CompatibleDriver,0,ref driver),"Enumerate compatible driver");
        var second = new DriverInfo { cbSize=driver.cbSize };
        bool another = SetupDiEnumDriverInfoW(set,ref dev,CompatibleDriver,1,ref second);
        int secondError = Marshal.GetLastWin32Error();
        if (another || secondError != 259) throw new InvalidOperationException("Expected exactly one compatible driver node.");
        DriverRecord record=Detail(set,ref dev,ref driver);
        if (!String.Equals(Path.GetFullPath(record.InfPath),inf,StringComparison.OrdinalIgnoreCase) ||
            !record.HardwareIds.StartsWith("USB\\VID_05C6&PID_9505",StringComparison.OrdinalIgnoreCase))
          throw new InvalidOperationException("Selected driver node is not the exact requested INF/EUD ID.");
        if (install) {
          InstallCalls++;
          Check(DiInstallDevice(IntPtr.Zero,set,ref dev,ref driver,0,out reboot),"Install specified driver on this one device");
        }
        return record;
      } finally {
        if (built) SetupDiDestroyDriverInfoList(set,ref dev,CompatibleDriver);
        SetupDiDestroyDeviceInfoList(set);
      }
    }
    public static DriverRecord Audit(string id, string inf) { bool reboot; return Select(id,inf,false,out reboot); }
    // Invoke only after the PowerShell environment/hash/ownership gates pass.
    public static BindingResult StageAndBind(string id, string sourceInf, string expectedInfSha256) {
      sourceInf=Path.GetFullPath(sourceInf);
      bool unused; Select(id,sourceInf,false,out unused);
      StageCalls++;
      var destination=new StringBuilder(512); uint required;
      Check(SetupCopyOEMInfW(sourceInf,Path.GetDirectoryName(sourceInf),1,0,destination,512,out required,IntPtr.Zero),"Stage one INF package without binding other devices");
      string published=destination.ToString();
      using (var sha=System.Security.Cryptography.SHA256.Create()) {
        string actual=BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(published))).Replace("-","").ToLowerInvariant();
        if (actual != expectedInfSha256) throw new InvalidOperationException("Staged INF digest differs; no binding attempted.");
      }
      bool reboot; Select(id,published,true,out reboot);
      return new BindingResult { PublishedInf=published, NeedReboot=reboot };
    }
  }
}
