CREATE TABLE ts
(
  area varchar(16),
  time TIMESTAMP,
  n int
);

COPY ts FROM '/home/postgres/empty_db.csv' DELIMITER ',' CSV HEADER;

CREATE TABLE weather
(
  time TIMESTAMP UNIQUE,
  temp REAL,
  current_rain REAL,
  rain_prob REAL,
  humidity REAL,
  wind REAL,
  cloud_cover REAL,
  uv INT
);
