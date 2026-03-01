-- Enable PostGIS in roof_db (runs once when the volume is created)
\connect roof_db
CREATE EXTENSION IF NOT EXISTS postgis;
