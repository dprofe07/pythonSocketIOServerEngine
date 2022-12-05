import random

from server import Server, Room


class MyRoom(Room):
    def __init__(self, game_name):
        super().__init__(game_name)
        self.guessed_num = random.randint(0, 100)


class MyServer(Server):
    def __init__(self, host, port):
        super().__init__(host, port, MyRoom)

    def on_disconnect(self, sid):
        self.leave_room(sid, self.get_session(sid).get('room'))

    @Server.sio_event('MyServer', 'check_number')
    def guess(self, sid, data):
        print(f'{self.get_session(sid)["login"]} думает: {data["n"]}')
        room = self.get_room_by_number(self.get_session(sid)['room'])

        if room.guessed_num > data['n']:
            self.emit('answer', {'result': 'greater'}, sid)
        elif room.guessed_num < data['n']:
            self.emit('answer', {'result': 'less'}, sid)
        else:
            self.emit('answer', {'result': 'equals'}, sid)
            self.emit(
                'winner',
                {
                    'login': self.get_session(sid)['login'],
                    'n': room.guessed_num
                },
                room=room.number,
                skip_sid=sid
            )

    @Server.sio_event('MyServer', 'join')
    def join(self, sid, data):
        ans = {
            'created': False,
            'joined': True
        }
        room = self.get_room_by_name(data["game_id"])
        if room is None:
            room = MyRoom(data['game_id'])
            self.rooms.append(room)
            ans['created'] = True

            print(f'Создана комната с id="{data["game_id"]}"')
            print(f'Пользователь {data["login"]} создал её')
        else:
            print(f'Пользователь {data["login"]} пытается присоединиться к {data["game_id"]}')
            if room.closed:
                print('Комната закрыта')
                ans['joined'] = False
            else:
                print('Успешно')

        if not ans['joined']:
            self.save_session(sid, {'login': data['login'], 'room': None})
        else:
            self.enter_room(sid, room.number)
            self.save_session(sid, {'login': data['login'], 'room': room.number})
            self.emit('new_user', {'login': data['login']}, room=room.number, skip_sid=sid)

        self.emit('join_answer', ans, sid)

    @Server.sio_event('MyServer', 'close_room')
    def close_room(self, sid, data):
        room = self.get_session(sid).get('room')
        if room is None:
            return
        self.get_room_by_number(room).close()

        self.emit('start_game', {})


srv = MyServer('0.0.0.0', 8007)

srv.run()