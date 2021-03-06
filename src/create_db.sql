-- Build the postgres database

CREATE TABLE ts
(
  area VARCHAR(16),
  district INT,
  tract BIGINT,
  time TIMESTAMP,
  N INT,
  in_use INT
);

COPY ts FROM '/home/postgres/new_ts.csv' DELIMITER ',' CSV HEADER;

ALTER TABLE ts ADD COLUMN bike_n INT;
ALTER TABLE ts ADD COLUMN bike_in_use INT;

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

CREATE TABLE predictions
(
  area VARCHAR(16),
  ds TIMESTAMP,
  yhat REAL,
  yhat_lower REAL,
  yhat_upper REAL,
  var VARCHAR(11)
 );

ALTER TABLE predictions ADD COLUMN modified_date TIMESTAMP;

--Create indices that should speed up querying
CREATE INDEX start_time ON rides(start_time);
CREATE INDEX time ON ts(time);
CREATE INDEX id ON rides(device_id);
CREATE INDEX ds_var ON predictions(ds, var);
