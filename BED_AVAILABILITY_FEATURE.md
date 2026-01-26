# Bed Availability Tracking Feature

## Overview

Implemented a comprehensive bed availability system that tracks how many beds are booked in each homestay across different date ranges and displays real-time availability status to users.

## Key Features Implemented

### 1. **Backend Availability Tracking Functions** (app.py)

#### `get_booked_beds_for_date_range(homestay_id, from_date_str, till_date_str)`

- Calculates total number of beds booked for a specific date range
- Counts beds from all overlapping confirmed/paid bookings
- Returns the sum of beds booked during the requested period

#### `get_available_beds_for_dates(homestay_id, from_date_str, till_date_str)`

- Calculates available beds for a date range
- Formula: Total Beds - Booked Beds = Available Beds
- Used during booking validation

#### `get_availability_status(homestay_id, days=7)`

- Generates 30-day availability calendar for a homestay
- Returns daily status with:
  - Number of available beds
  - Total beds
  - Whether fully booked (boolean)
  - Number of booked beds

### 2. **Booking Validation**

The `/book/<homestay_id>` route now:

- Accepts `beds_requested` parameter from the form
- Validates that requested beds are available for selected dates
- Shows error message if insufficient beds available
- Displays remaining available beds in the error

### 3. **Bed Tracking in Bookings**

- Added `beds_booked` field to all new booking records
- Stored in the bookings table to track how many beds each booking occupies
- Defaults to 1 bed if not specified (backward compatible)

### 4. **Frontend - Room Listing** (rooms.html)

Each homestay card now displays:

- **Availability Badge** (top-right corner)
  - Green badge: "X/Y beds available" for available properties
  - Red badge: "Fully Booked" for fully booked properties
- Updates in real-time based on today's availability

### 5. **Frontend - Book Homestay Page** (book_homestay.html)

Enhanced booking form with:

- **Beds Selection Dropdown**: Choose 1-N beds (where N = total beds in homestay)
- **Dynamic Availability Display**:
  - Shows available beds when dates and bed count are selected
  - Green indicator (✓): Beds are available
  - Red indicator (✗): Insufficient beds available
  - Orange warning (⚠️): Fully booked for selected dates
- **Smart Button State**: Submit button disabled until valid selection
- **Real-time Validation**: Updates as user selects dates and beds

### 6. **Frontend - Homestay Details Page** (homestay_details.html)

Shows a **30-Day Availability Calendar** with:

- Color-coded calendar grid
  - **Blue**: Beds available (shows X/Y beds available)
  - **Orange**: Partially booked (some beds available)
  - **Red**: Fully booked
- Hover tooltips showing detailed availability
- Legend explaining color meanings

## Database Schema Changes

The `bookings` table now includes:

- `beds_booked` (integer): Number of beds reserved in this booking

This field is automatically populated when creating new bookings.

## How It Works - Example Scenario

**Example**: Homestay has 4 total beds

1. **User A books**: 1 bed from Jan 26-28
   - Remaining available: 3 beds

2. **User B books**: 2 beds from Jan 27-29
   - Both User A and B overlap on Jan 27-28
   - Jan 27-28: 1 (A) + 2 (B) = 3 beds booked, 1 bed available
   - Jan 26: 1 bed booked, 3 available
   - Jan 28: 3 beds booked, 1 available
   - Jan 29: 2 beds booked, 2 available

3. **User C tries to book**: 2 beds for Jan 27-28
   - System checks: Only 1 bed available on Jan 27-28
   - Booking rejected with message: "Only 1 bed(s) available for your selected dates"

## User Interface Updates

### Rooms Page

- Shows quick availability status badge on each card
- Users can see at a glance which properties have beds available

### Booking Page

- Users select number of beds they want
- System validates availability before payment
- Clear feedback on bed availability for selected dates

### Homestay Details

- Comprehensive 30-day calendar view
- Users can see availability trends before booking
- Color-coded visual representation

## Benefits

1. **Better Resource Management**: Track exactly how many beds are booked
2. **Accurate Availability**: Real-time calculation prevents overbooking
3. **User Experience**: Clear visibility of what's available before booking
4. **Flexible Bookings**: Users can book partial homestays (multiple users can share)
5. **Data-Driven**: Calendar view helps users choose best booking dates

## Files Modified

1. `app.py` - Added availability functions and updated routes
2. `templates/rooms.html` - Added availability badges
3. `templates/book_homestay.html` - Added beds selection and validation
4. `templates/homestay_details.html` - Added 30-day calendar view
