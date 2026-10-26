"""Bounded LOC client for temporary NMEA diagnostics; no NV or RF controls."""
import gi
gi.require_version('Qmi','1.0')
gi.require_version('Qrtr','1.0')
from gi.repository import Qmi,Qrtr,GLib,Gio


def await_call(start,finish,seconds=15):
    loop=GLib.MainLoop();cancel=Gio.Cancellable();state={}
    def done(source,result,*_):
        try:state['result']=finish(source,result)
        except Exception as error:state['error']=error
        state['completed']=True;loop.quit()
    def expired():
        state['expired']=True;cancel.cancel();return False
    def abandon():
        state['abandoned']=True;loop.quit();return False
    timers=[GLib.timeout_add_seconds(seconds,expired),GLib.timeout_add_seconds(seconds+10,abandon)]
    try:
        start(cancel,done)
        loop.run()
    finally:
        for timer in timers:
            if GLib.MainContext.default().find_source_by_id(timer):GLib.source_remove(timer)
    if state.get('expired') or state.get('abandoned'):raise TimeoutError('LOC operation deadline; inspect same operation')
    if 'error' in state:raise state['error']
    assert state.get('completed')
    return state['result']


def pump_until(predicate,seconds):
    if predicate():return True
    loop=GLib.MainLoop()
    def poll():
        if predicate():loop.quit();return False
        return True
    def expired():loop.quit();return False
    timers=[GLib.timeout_add(20,poll),GLib.timeout_add_seconds(seconds,expired)]
    try:loop.run()
    finally:
        for timer in timers:
            if GLib.MainContext.default().find_source_by_id(timer):GLib.source_remove(timer)
    return bool(predicate())


class LocSession:
    def __init__(self):
        self.bus=self.device=self.client=None
        self.signals=[];self.receipts=[]

    def open(self):
        self.bus=await_call(lambda cancel,cb:Qrtr.Bus.new(2000,cancel,cb,None),lambda source,res:Qrtr.Bus.new_finish(res))
        node=self.bus.get_node(0)
        assert node is not None
        self.device=await_call(lambda cancel,cb:Qmi.Device.new_from_node(node,cancel,cb,None),lambda source,res:Qmi.Device.new_from_node_finish(res))
        assert await_call(lambda cancel,cb:self.device.open(Qmi.DeviceOpenFlags.EXPECT_INDICATIONS,10,cancel,cb,None),lambda source,res:source.open_finish(res))
        self.client=await_call(lambda cancel,cb:self.device.allocate_client(Qmi.Service.LOC,Qmi.CID_NONE,10,cancel,cb,None),lambda source,res:source.allocate_client_finish(res))
        return self

    def connect(self,name,callback):
        handler=self.client.connect(name,callback);self.signals.append(handler)
        return handler

    def nmea_mask(self,value=None):
        operation='get' if value is None else 'set'
        received=[]
        signal=self.client.connect(operation+'-nmea-types',lambda _client,output:received.append(output))
        receipt=dict(operation=operation,ack=False,indication=False)
        try:
            request=None
            if value is not None:
                request=Qmi.MessageLocSetNmeaTypesInput.new()
                request.set_nmea_types(Qmi.LocNmeaType(value))
            output=await_call(lambda cancel,cb:getattr(self.client,operation+'_nmea_types')(request,10,cancel,cb,None),lambda source,res:getattr(source,operation+'_nmea_types_finish')(res))
            output.get_result();receipt['ack']=True
            assert pump_until(lambda:bool(received),12),'No LOC NMEA result indication'
            assert len(received)==1
            receipt['indication']=True
            receipt['status']=int(received[0].get_indication_status())
            assert receipt['status']==0,'LOC NMEA request rejected'
            if value is None:receipt['mask']=int(received[0].get_nmea_types())
            else:receipt['mask']=value
            return receipt['mask']
        finally:
            self.client.disconnect(signal);self.receipts.append(receipt)

    def register(self,mask):
        request=Qmi.MessageLocRegisterEventsInput.new()
        request.set_event_registration_mask(Qmi.LocEventRegistrationFlag(mask))
        output=await_call(lambda cancel,cb:self.client.register_events(request,10,cancel,cb,None),lambda source,res:source.register_events_finish(res))
        output.get_result()

    def close(self):
        result=dict(client_released=self.client is None,device_closed=self.device is None)
        if self.client is not None:
            for handler in self.signals:self.client.disconnect(handler)
            result['client_released']=bool(await_call(lambda cancel,cb:self.device.release_client(self.client,Qmi.DeviceReleaseClientFlags.RELEASE_CID,10,cancel,cb,None),lambda source,res:source.release_client_finish(res)))
            self.client=None
        if self.device is not None:
            result['device_closed']=bool(await_call(lambda cancel,cb:self.device.close_async(10,cancel,cb,None),lambda source,res:source.close_finish(res)))
            self.device=None
        return result
