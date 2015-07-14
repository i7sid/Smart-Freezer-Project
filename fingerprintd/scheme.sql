CREATE TABLE IF NOT EXISTS users (
  id integer primary key AUTOINCREMENT not null,
  name char(50) unique not null
);

CREATE TABLE IF NOT EXISTS user_fingerprints (
  id integer primary key AUTOINCREMENT not null,
  user_id integer,
  fingerprint_id integer,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_bookings (
  id integer primary key AUTOINCREMENT not null,
  user_id integer,
  booking_date datetime,
  count integer,
  type integer,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS user_fingerprint_idx ON user_fingerprints (user_id, fingerprint_id);
