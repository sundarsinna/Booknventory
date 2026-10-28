-- Store each book's series emoji instead of mapping icons in application code.
ALTER TABLE books
ADD COLUMN IF NOT EXISTS series_emoji TEXT;

-- Preserve the existing DOG MAN and INVESTIGATORS display icons.
UPDATE books
SET series_emoji = CASE LOWER(TRIM(series_name))
    WHEN 'dog man' THEN '🐶'
    WHEN 'investigators' THEN '🐊'
END
WHERE series_emoji IS NULL
  AND LOWER(TRIM(series_name)) IN ('dog man', 'investigators');
