# Migration Guide: Add Missing Columns to Bookings Table

## Issues

The bed availability tracking feature and enhanced booking system require additional columns in the `bookings` table.

## Required Columns

These columns need to be added to your Supabase `bookings` table:

| Column        | Type    | Default | Purpose                                                 |
| ------------- | ------- | ------- | ------------------------------------------------------- |
| `beds_booked` | INTEGER | 1       | Track how many beds each booking reserves               |
| `user_email`  | TEXT    | NULL    | Store user's email for booking records                  |
| `user_name`   | TEXT    | NULL    | Store user's name for booking records                   |
| `user_phone`  | TEXT    | NULL    | Store user's phone for booking records (already exists) |

## Solution: Add All Missing Columns

### Option A: Add Columns Individually

Run these SQL queries one at a time in Supabase SQL Editor:

```sql
ALTER TABLE bookings
ADD COLUMN beds_booked INTEGER DEFAULT 1;

ALTER TABLE bookings
ADD COLUMN user_email TEXT;

ALTER TABLE bookings
ADD COLUMN user_name TEXT;
```

### Option B: Add All at Once

Run this single query in Supabase SQL Editor:

```sql
ALTER TABLE bookings
ADD COLUMN IF NOT EXISTS beds_booked INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS user_email TEXT,
ADD COLUMN IF NOT EXISTS user_name TEXT;
```

### Step 2: Verify Columns Were Added

Run this query to verify all columns exist:

```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name='bookings'
AND column_name IN ('beds_booked', 'user_email', 'user_name', 'user_phone')
ORDER BY column_name;
```

You should see 4 rows with these columns.

## What Each Column Does

- **beds_booked**: Tracks how many beds the booking reserves (enables multi-bed bookings and availability calculation)
- **user_email**: Stores customer email for booking reference and notifications
- **user_name**: Stores customer name for booking records
- **user_phone**: Stores customer phone number (should already exist)

## Example Data Structure

```
booking_id | homestay_id | from_date  | till_date   | beds_booked | user_name  | user_email        | user_phone
-----------|-------------|------------|-------------|-------------|------------|-------------------|---------------
1          | 1           | 2026-01-26 | 2026-01-29  | 1           | John Doe   | john@example.com  | 9876543210
2          | 1           | 2026-01-27 | 2026-01-30  | 2           | Jane Smith | jane@example.com  | 9876543211
```

## After Migration

1. Stop your Flask app: `Ctrl+C`
2. Run the SQL queries above in Supabase
3. Restart Flask: `python app.py`
4. Test a booking - it should work without errors!

## Troubleshooting

**Error**: "Could not find the 'user_email' column"

- Solution: Run the SQL query above to add the column

**Error**: "Column already exists"

- Solution: The column is already added. Just restart Flask.

**Multiple columns missing**

- Solution: Use Option B (add all at once) to add them all in one query

**Bookings still failing**

- Solution: Verify columns exist using the verification query
- Check column types match (all should be TEXT or INTEGER as shown)

## Rollback (If Needed)

If you need to remove columns:

```sql
ALTER TABLE bookings DROP COLUMN IF EXISTS beds_booked;
ALTER TABLE bookings DROP COLUMN IF EXISTS user_email;
ALTER TABLE bookings DROP COLUMN IF EXISTS user_name;
```

Then restart Flask - it will work in backward compatibility mode.

## Code Behavior

The application now has smart error handling:

- If a column doesn't exist, it will skip that field and retry
- Bookings will still be created even if some columns are missing
- Error messages will tell you which columns to add
- Once columns are added, they'll be automatically used
