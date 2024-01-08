DROP TABLE IF EXISTS environmental_data;
CREATE TABLE environmental_data(timestamp DATETIME, temperature NUMERIC, humidity NUMERIC);
DROP TABLE IF EXISTS aiq_data;
CREATE TABLE aiq_data(timestamp DATETIME, tvoc NUMERIC, eco2 NUMERIC);