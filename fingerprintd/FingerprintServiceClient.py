import zmq
import json

class FingerprintServiceClient:
    socket = None

    def __init__(self, port = 5757):
        context = zmq.Context()
        self.socket = context.socket(zmq.REQ)
        self.socket.connect ("tcp://127.0.0.1:5758")

    def get_users(self):
        msg = {
            'command': 'get_users'
        }
        return json.loads(self._send_to_socket(msg))

    def get_user(self, user_id):
        msg = {
            'command': 'get_user',
            'user_id': user_id
        }
        return json.loads(self._send_to_socket(msg))

    def get_bookings(self, user_id):
        msg = {
            'command': 'get_bookings',
            'user_id': user_id
        }
        return json.loads(self._send_to_socket(msg))

    def remove_user(self, user_id):
        msg = {
            'command': 'remove_user',
            'user_id': user_id
        }
        return json.loads(self._send_to_socket(msg))

    def get_state(self):
        msg = {
            'command': 'get_state'
        }
        return self._send_to_socket(msg)

    def remove_fingerprint(self, fingerprint_id):
        msg = {
            'command': 'remove_fingerprint',
            'fingerprint_id': fingerprint_id
        }
        return self._send_to_socket(msg)

    def add_booking(self, user_id, count, type = 2):
        msg = {
            'command': 'add_booking',
            'user_id': user_id,
            'count': count,
            'type': type
        }
        return self._send_to_socket(msg)

    def change_user(self, user):
        msg = {
            'command': 'change_user',
            'user': user
        }
        return json.loads(self._send_to_socket(msg))

    def enroll(self, user_id):
        msg = {
            'command': 'enroll',
            'user_id': user_id
        }
        return json.loads(self._send_to_socket(msg))

    def add_user(self, name):
        msg = {
            'command': 'add_user',
            'name': name
        }
        ret = self._send_to_socket(msg)
        print ret
        return json.loads(ret)

    def _send_to_socket(self, msg):
        self.socket.send (json.dumps(msg))
        return self.socket.recv()

if __name__ == '__main__':
    client = FingerprintServiceClient()
    client.get_users()
