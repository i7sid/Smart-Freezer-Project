import sqlite3

class UserDB:
    conn = None

    def __init__(self):
        self.conn = sqlite3.connect("accounting.db")
        c = self.conn.cursor()
        scheme = file("scheme.sql").read()
        c.executescript(scheme)

    def get_users(self, id = 0):
        res = None
        c = self.conn.cursor()
        if id:
            res = c.execute('SELECT * FROM users WHERE id = ?', (id, ));
        else:
            res = c.execute('SELECT * FROM users');

        ret = []
        for row in res:
            ret.append({
                'id': row[0],
                'name': row[1],
                'fingerprints': self.get_fingerprints(row[0]),
                'bookingcount': self.get_bookingcount(row[0])
            })
        return ret

    def add_booking(self, user_id, count, type = 1):
        c = self.conn.cursor()
        c.execute("insert into user_bookings (user_id, count, booking_date, type) values (?, ?, datetime('now'), ?);", (user_id, count, type))
        self.conn.commit()
        return c.lastrowid

    def get_bookings(self, user_id = 0):
        c = self.conn.cursor()
        if user_id:
            res = c.execute('SELECT user_id, booking_date, count, type FROM user_bookings WHERE user_id = ? ORDER BY booking_date DESC', (user_id, ));
        else:
            res = c.execute('SELECT user_id, booking_date, count, type FROM user_bookings');

        ret = []
        for row in res:
            ret.append({
                'user_id': row[0],
                'booking_date': row[1],
                'count': row[2],
                'type': row[3]
            })
        return ret

    def get_fingerprints(self, user_id):
        c = self.conn.cursor()
        res = c.execute('SELECT fingerprint_id FROM user_fingerprints WHERE user_id = ?', (user_id, ));
        ret = []
        for row in res:
            ret.append(row[0])
        return ret

    def get_bookingcount(self, user_id):
        c = self.conn.cursor()
        c.execute('SELECT SUM(count) FROM user_bookings WHERE user_id = ?', (user_id, ));
        res = c.fetchone()
        if res:
            if res[0] == None:
                return 0;
            return res[0]
        return None

    def add_fingerprint(self, user_id, fingerprint_id):
        c = self.conn.cursor()
        c.execute("insert into user_fingerprints (user_id, fingerprint_id) values (?, ?);", (user_id, fingerprint_id))
        self.conn.commit()
        return c.lastrowid

    def remove_fingerprint(self, user_id, fingerprint_id):
        c = self.conn.cursor()
        c.execute("delete from user_fingerprints where user_id = ? and fingerprint_id = ?", (user_id, fingerprint_id))
        self.conn.commit()

    def get_user_by_fingerprint(self, fingerprint_id):
        c = self.conn.cursor()
        c.execute('SELECT user_id FROM user_fingerprints WHERE fingerprint_id = ? ', (fingerprint_id, ))
        res = c.fetchone()
        if res:
            return self.get_user(res[0])
        return None

    def get_user(self, user_id):
        users = self.get_users(user_id)
        if len(users) > 0:
            return users[0]
        return None

    def add_user(self, username):
        c = self.conn.cursor()
        c.execute("insert into users (name) values (?);", (''+username,))
        self.conn.commit()
        return c.lastrowid

    def del_user(self, user_id):
        c = self.conn.cursor()
        c.execute("delete from users where id = ?", (user_id,))
        self.conn.commit()

    def update_user(self, user_id, username):
        c = self.conn.cursor()
        c.execute("update users set name = ? where id = ?", (username, user_id,))
        self.conn.commit()

if __name__ == '__main__':
    users = UserDB()
    print users.get_user(2)
    users.add_fingerprint(2, 20)
    print users.get_user_by_fingerprint(20)
    users.remove_fingerprint(2, 20)
