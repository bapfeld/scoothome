CREATE TABLE ts
(
  area varchar(16),
  time TIMESTAMP,
  n int
);

COPY ts FROM '/home/postgres/empty_db.csv' DELIMITER ',' CSV HEADER;
