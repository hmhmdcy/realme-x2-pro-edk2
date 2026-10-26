// RX55: read-only GET_STATS on the existing .NET Framework serial handle.
// Its own manual event has bit 0 set in OVERLAPPED.hEvent: this query must
// not deliver an unmanaged OVERLAPPED to SerialStream's CLR completion port.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO.Ports;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using Microsoft.Win32.SafeHandles;

public sealed class EudPerfSample {
    public uint received, transmitted, frame_errors, serial_overruns;
    public uint buffer_overruns, parity_errors, returned;
    public bool initially_pending;
    public long query_ms;
    public string raw_hex;
}

public sealed class EudSerialPerf : IDisposable {
    public const uint GetStatsCode = (0x1bu << 16) | (35u << 2);
    [StructLayout(LayoutKind.Sequential)]
    private struct NativeOverlap {
        public IntPtr Internal, InternalHigh;
        public uint Offset, OffsetHigh;
        public IntPtr Event;
    }
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool DeviceIoControl(SafeFileHandle handle, uint code,
        IntPtr input, uint inputSize, IntPtr output, uint outputSize,
        out uint returned, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetOverlappedResultEx(SafeFileHandle handle,
        IntPtr overlapped, out uint returned, uint timeout, bool alertable);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CancelIoEx(SafeFileHandle handle, IntPtr overlapped);

    private sealed class QueryStorage {
        public readonly EventWaitHandle Event = new EventWaitHandle(false, EventResetMode.ManualReset);
        public IntPtr overlap, output;
        public QueryStorage() {
            try {
                overlap = Marshal.AllocHGlobal(OverlapSize);
                output = Marshal.AllocHGlobal(24);
                Marshal.Copy(new byte[OverlapSize], 0, overlap, OverlapSize);
                Marshal.Copy(new byte[24], 0, output, 24);
                IntPtr eventWithLowBit = new IntPtr(Event.SafeWaitHandle.DangerousGetHandle().ToInt64() | 1L);
                Marshal.WriteIntPtr(overlap, EventOffset, eventWithLowBit);
            } catch { Free(); throw; }
        }
        public void Free() {
            if (overlap != IntPtr.Zero) { Marshal.FreeHGlobal(overlap); overlap = IntPtr.Zero; }
            if (output != IntPtr.Zero) { Marshal.FreeHGlobal(output); output = IntPtr.Zero; }
            Event.Dispose();
        }
    }
    // At most one stalled request per bounded owner. Retain its event and
    // native buffers for process lifetime if cancellation/close hasn't yet
    // signalled completion; freeing on a cancellation request is unsafe.
    private static readonly List<QueryStorage> Retained = new List<QueryStorage>();
    public static int OverlapSize { get { return Marshal.SizeOf(typeof(NativeOverlap)); } }
    public static int EventOffset { get { return (int)Marshal.OffsetOf(typeof(NativeOverlap), "Event"); } }
    public static int RetainedCount { get { lock (Retained) return Retained.Count; } }
    private readonly SafeFileHandle handle;
    private QueryStorage stalled;
    private bool disposed;
    public bool HasStalledQuery { get { return stalled != null; } }
    public EudSerialPerf(SerialPort port) {
        object stream = port.BaseStream;
        if (stream.GetType().FullName != "System.IO.Ports.SerialStream")
            throw new NotSupportedException("Expected .NET Framework SerialStream.");
        BindingFlags flags = BindingFlags.NonPublic | BindingFlags.Instance;
        FieldInfo handleField = stream.GetType().GetField("_handle", flags);
        FieldInfo asyncField = stream.GetType().GetField("isAsync", flags);
        if (handleField == null || asyncField == null || !(bool)asyncField.GetValue(stream))
            throw new NotSupportedException("Expected existing overlapped SerialStream handle.");
        handle = handleField.GetValue(stream) as SafeFileHandle;
        if (handle == null || handle.IsInvalid || handle.IsClosed)
            throw new NotSupportedException("Expected open serial SafeFileHandle.");
    }
    public EudPerfSample Sample() {
        if (disposed) throw new ObjectDisposedException("EudSerialPerf");
        if (stalled != null) throw new InvalidOperationException("Previous GET_STATS hasn't completed; stop this owner.");
        QueryStorage storage = new QueryStorage();
        bool completed = true;
        Stopwatch timer = Stopwatch.StartNew();
        try {
            uint returned;
            bool immediate = DeviceIoControl(handle, GetStatsCode, IntPtr.Zero, 0,
                storage.output, 24, out returned, storage.overlap);
            int initialError = immediate ? 0 : Marshal.GetLastWin32Error();
            if (!immediate && initialError != 997) throw new Win32Exception(initialError, "GET_STATS submission");
            completed = immediate;
            bool success = GetOverlappedResultEx(handle, storage.overlap, out returned, 500, false);
            int resultError = success ? 0 : Marshal.GetLastWin32Error();
            completed = completed || success || storage.Event.WaitOne(0);
            if (!completed) {
                bool canceled = CancelIoEx(handle, storage.overlap); // this query only, never NULL
                int cancelError = canceled ? 0 : Marshal.GetLastWin32Error();
                bool settled = GetOverlappedResultEx(handle, storage.overlap, out returned, 500, false);
                int settleError = settled ? 0 : Marshal.GetLastWin32Error();
                completed = settled || storage.Event.WaitOne(0);
                throw new TimeoutException("GET_STATS wait failed: " + resultError +
                    "; query-only cancel=" + cancelError + "; settle=" + settleError +
                    "; completed=" + completed);
            }
            if (!success) throw new Win32Exception(resultError, "GET_STATS completion");
            if (returned != 24) throw new InvalidOperationException("GET_STATS returned " + returned + " bytes; expected 24.");
            byte[] bytes = new byte[24];
            Marshal.Copy(storage.output, bytes, 0, 24);
            return new EudPerfSample {
                received = BitConverter.ToUInt32(bytes, 0), transmitted = BitConverter.ToUInt32(bytes, 4),
                frame_errors = BitConverter.ToUInt32(bytes, 8), serial_overruns = BitConverter.ToUInt32(bytes, 12),
                buffer_overruns = BitConverter.ToUInt32(bytes, 16), parity_errors = BitConverter.ToUInt32(bytes, 20),
                returned = returned, initially_pending = !immediate, query_ms = timer.ElapsedMilliseconds,
                raw_hex = BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant()
            };
        } finally {
            if (completed) storage.Free();
            else stalled = storage;
        }
    }
    public void Dispose() {
        if (disposed) return;
        disposed = true;
        // The caller closes SerialPort first; its handle ownership stays there.
        if (stalled != null) {
            if (stalled.Event.WaitOne(500)) stalled.Free();
            else lock (Retained) Retained.Add(stalled);
            stalled = null;
        }
    }
}
