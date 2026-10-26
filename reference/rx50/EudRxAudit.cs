// Read-only diagnostic attached to an existing .NET Framework SerialPort owner.
// Sample replaces BytesToRead's ClearCommError call, preserving returned flags.
// No second open, purge, buffer reconfiguration, USB reset or device write.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO.Ports;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public sealed class EudErrorNotice {
    public long ms;
    public int error;
    public string name;
}
public sealed class EudCommSample {
    public uint errors;
    public uint flags;
    public uint in_queue;
    public uint out_queue;
}
public sealed class EudRxAudit : IDisposable {
    [StructLayout(LayoutKind.Sequential)]
    private struct ComStat { public uint flags, inQueue, outQueue; }
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool ClearCommError(SafeFileHandle handle, out uint errors, out ComStat stat);
    private readonly SerialPort port;
    private readonly Stopwatch clock;
    private readonly SafeFileHandle handle;
    private readonly FieldInfo readPos, readLen;
    private readonly Queue<EudErrorNotice> notices = new Queue<EudErrorNotice>();
    public EudRxAudit(SerialPort port, Stopwatch clock) {
        this.port = port;
        this.clock = clock;
        object stream = port.BaseStream;
        if (stream.GetType().FullName != "System.IO.Ports.SerialStream")
            throw new NotSupportedException("Expected .NET Framework SerialStream.");
        FieldInfo field = stream.GetType().GetField("_handle", BindingFlags.NonPublic | BindingFlags.Instance);
        if (field == null) throw new NotSupportedException("SerialStream handle unavailable.");
        handle = field.GetValue(stream) as SafeFileHandle;
        if (handle == null || handle.IsInvalid || handle.IsClosed)
            throw new NotSupportedException("Expected open SafeFileHandle.");
        readPos = typeof(SerialPort).GetField("readPos", BindingFlags.NonPublic | BindingFlags.Instance);
        readLen = typeof(SerialPort).GetField("readLen", BindingFlags.NonPublic | BindingFlags.Instance);
        if (readPos == null || readLen == null)
            throw new NotSupportedException("SerialPort cache fields unavailable.");
        port.ErrorReceived += OnError;
    }
    private void OnError(object sender, SerialErrorReceivedEventArgs args) {
        lock (notices) notices.Enqueue(new EudErrorNotice {
            ms = clock.ElapsedMilliseconds, error = (int)args.EventType, name = args.EventType.ToString()
        });
    }
    public EudCommSample Sample() {
        // This terminal only reads byte arrays; a cached character read would
        // invalidate cbInQue == BytesToRead. Fail rather than silently omit it.
        if ((int)readLen.GetValue(port) != (int)readPos.GetValue(port))
            throw new NotSupportedException("Unexpected SerialPort cached bytes.");
        uint errors;
        ComStat stat;
        if (!ClearCommError(handle, out errors, out stat))
            throw new Win32Exception(Marshal.GetLastWin32Error());
        return new EudCommSample { errors = errors, flags = stat.flags,
                                  in_queue = stat.inQueue, out_queue = stat.outQueue };
    }
    public EudErrorNotice[] Drain() {
        lock (notices) { EudErrorNotice[] result = notices.ToArray(); notices.Clear(); return result; }
    }
    public void Dispose() { port.ErrorReceived -= OnError; } // port retains handle ownership

    // Identify the installed managed implementation without opening any port.
    public static string[] Calls(MethodInfo method) {
        Dictionary<ushort, OpCode> codes = new Dictionary<ushort, OpCode>();
        foreach (FieldInfo field in typeof(OpCodes).GetFields(BindingFlags.Public | BindingFlags.Static)) {
            if (field.FieldType == typeof(OpCode)) {
                OpCode op = (OpCode)field.GetValue(null); codes[unchecked((ushort)op.Value)] = op;
            }
        }
        List<string> calls = new List<string>();
        byte[] il = method.GetMethodBody().GetILAsByteArray();
        for (int pos = 0; pos < il.Length;) {
            int start = pos;
            ushort value = il[pos++];
            if (value == 0xfe) value = (ushort)(0xfe00 | il[pos++]);
            OpCode op = codes[value];
            switch (op.OperandType) {
                case OperandType.InlineMethod:
                    int token = BitConverter.ToInt32(il, pos);
                    MethodBase called = method.Module.ResolveMethod(token);
                    calls.Add(start.ToString("x4") + " " + op.Name + " " + called.DeclaringType.FullName + "." + called.Name);
                    pos += 4; break;
                case OperandType.InlineNone: break;
                case OperandType.ShortInlineBrTarget:
                case OperandType.ShortInlineI:
                case OperandType.ShortInlineVar: pos++; break;
                case OperandType.InlineVar: pos += 2; break;
                case OperandType.InlineI8:
                case OperandType.InlineR: pos += 8; break;
                case OperandType.InlineSwitch:
                    pos += 4 + 4 * BitConverter.ToInt32(il, pos); break;
                default: pos += 4; break;
            }
        }
        return calls.ToArray();
    }
}
