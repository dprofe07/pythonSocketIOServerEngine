import functools
from collections import defaultdict

import socketio
import eventlet


class Room:
    next_number = 1

    def __init__(self, name):
        self.closed = False
        self.number = Room.next_number
        self.name = name
        self.users_count = 0
        Room.next_number += 1

    def close(self):
        self.closed = True


class Server:
    _methods = defaultdict(list)

    def __init__(self, host, port, room_class=Room):
        self.room_class = room_class
        self.host = host
        self.port = port
        self.sio = socketio.Server()
        self.app = socketio.WSGIApp(self.sio)

        self.events_data = defaultdict(lambda: False)
        self.rooms = []

        self._on_connect = self.sio.on('connect')(self._on_connect)
        self._on_disconnect = self.sio.on('disconnect')(self._on_disconnect)
        self._on_any_event = self.sio.on('*')(self._on_any_event)

        for method, event in Server._methods[self.__class__.__name__]:
            setattr(self, method, self.sio.on(event)(getattr(self, method)))

    def get_room_by_number(self, num):
        for r in self.rooms:
            if r.number == num:
                return r
        return None

    def get_room_by_name(self, name):
        for r in self.rooms:
            if r.name == name:
                return r
        return None

    def on_connect(self, sid, environ):
        pass

    def _on_connect(self, sid, environ):
        pass

    def _on_disconnect(self, sid):
        room_n = self.get_session(sid).get('room')
        if room_n is not None:
            self.leave_room(sid, room_n)

    def on_disconnect(self, sid):
        pass

    def _on_any_event(self, event, sid, data):
        self.events_data[event] = True
        self.on_any_event(event, sid, data)

    def on_any_event(self, event, sid, data):
        pass

    def emit(self, evt, data, to=None, room=None, skip_sid=None):
        self.sio.emit(evt, data, to, room, skip_sid)

    def enter_room(self, sid, room):
        rm = self.get_room_by_number(room)
        if rm is not None:
            rm.users_count += 1

        self.sio.enter_room(sid, room)

    def leave_room(self, sid, room):
        rm = self.get_room_by_number(room)
        if rm is not None:
            rm.users_count -= 1
            if rm.users_count <= 0 and rm.closed:
                self.rooms.remove(rm)
        self.sio.leave_room(sid, room)

    def get_session(self, sid):
        return self.sio.get_session(sid)

    def save_session(self, sid, session):
        self.sio.save_session(sid, session)

    def run(self):
        eventlet.wsgi.server(eventlet.listen((self.host, self.port)), self.app)

    @staticmethod
    def sio_event(class_name, event):
        def decor(method):
            Server._methods[class_name].append((method.__name__, event))

            @functools.wraps(method)
            def wrapper(*a, **kw):
                return method(*a, **kw)

            return wrapper

        return decor
