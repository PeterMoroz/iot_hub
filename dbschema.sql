DROP TABLE IF EXISTS th_sensor_data;
DROP TABLE IF EXISTS aiq_sensor_data;

CREATE TABLE th_sensor_data (
    ts TIMESTAMP NOT NULL,
    temperature REAL NOT NULL,
    humidity REAL NOT NULL
);

CREATE TABLE aiq_sensor_data (
    ts TIMESTAMP NOT NULL,
    co2 INTEGER NOT NULL,
    tvoc INTEGER NOT NULL
);