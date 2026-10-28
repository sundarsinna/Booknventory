-- Make missing book prices default to zero and repair existing missing/NaN prices.
ALTER TABLE books
ALTER COLUMN purchase_price SET DEFAULT 0;

UPDATE books
SET purchase_price = 0
WHERE purchase_price IS NULL
   OR purchase_price::text IN ('NaN', 'nan', '-NaN');
