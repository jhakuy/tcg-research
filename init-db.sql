-- Initialize TimescaleDB and create hypertables

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create hypertables for time-series data after tables are created
-- These will be run after alembic migrations

-- Note: Hypertables are created in the application code after schema creation
-- because alembic doesn't handle TimescaleDB hypertables well

-- Create indexes for common queries
-- These will be created via alembic migrations