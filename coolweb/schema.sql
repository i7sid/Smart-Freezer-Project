drop table if exists power_consumption;
drop table if exists epex_prices;

create table power_consumption (
  id integer primary key autoincrement,
  day text not null,
  hour integer not null,
  amount real not null
);

create table epex_prices (
  id integer primary key autoincrement,
  day text not null,
  hour integer not null,
  price real not null
);