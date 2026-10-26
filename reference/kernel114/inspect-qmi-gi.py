import gi
gi.require_version('Qmi','1.0')
gi.require_version('Qrtr','1.0')
from gi.repository import Qmi, Qrtr, GObject
for cls,names in [(Qrtr.Bus,['peek_node','get_node','new_finish']),(Qmi.Device,['open','open_finish','new_from_node_finish','allocate_client_finish','release_client']),(Qmi.MessageLocRegisterEventsInput,['new','set_event_registration_mask']),(Qmi.MessageLocStartInput,['new','set_session_id','set_recurrence_type','set_intermediate_report_state']),(Qmi.MessageLocStopInput,['new','set_session_id'])]:
    print(cls.__name__)
    for name in names:
        method=getattr(cls,name,None)
        print(name,method.__doc__ if method else 'absent')
print('CID_NONE',Qmi.CID_NONE)
for name in ['DeviceOpenFlags','LocEventRegistrationFlag','LocIntermediateReportState']:
    cls=getattr(Qmi,name)
    print(name,[n for n in dir(cls) if n.isupper()])
print('signals',GObject.signal_list_names(Qmi.ClientLoc))
print('start setters',[n for n in dir(Qmi.MessageLocStartInput) if n.startswith('set_')])
