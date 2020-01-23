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

CREATE TABLE rides
(
  trip_id CHAR(36),
  device_id CHAR(36),
  vehicle_type TEXT,
  duration REAL,
  distance REAL,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  modified_date TIMESTAMP,
  month SMALLINT,
  hour SMALLINT,
  day_of_week SMALLINT,
  council_district_start INT,
  council_district_end INT,
  year SMALLINT,
  census_tract_start BIGINT,
  census_tract_end BIGINT
);

COPY rides FROM '/home/postgres/rides.csv' DELIMITER ',' CSV HEADER;
