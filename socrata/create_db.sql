CREATE TABLE ts
(
  area VARCHAR(16),
  district INT,
  tract BIGINT,
  time TIMESTAMP,
  N INT
);

COPY ts FROM '/home/postgres/db.csv' DELIMITER ',' CSV HEADER;

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
