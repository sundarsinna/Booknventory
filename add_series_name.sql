-- Add an optional series title while preserving existing book records.
ALTER TABLE books
ADD COLUMN IF NOT EXISTS series_name VARCHAR(255);
