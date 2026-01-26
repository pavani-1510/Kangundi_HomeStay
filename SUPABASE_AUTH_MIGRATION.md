# Supabase Authentication Migration

## Overview

The Kangundi_HomeStay app has been migrated from using a custom `users` table to Supabase's built-in authentication system (`auth.users`).

## Key Changes

### 1. User Storage

- **Before**: Users stored in custom `users` table with columns: `id`, `name`, `phone_number`, `username`, `password_hash`, `is_admin`, `created_at`
- **After**: Users stored in Supabase `auth.users` with:
  - Core fields: `id`, `email`, `phone`, `created_at`
  - Custom data in `user_metadata`: `name`, `phone_number`, `username`, `is_admin`

### 2. Authentication Methods

#### Phone + OTP Login (Regular Users)

- Uses `supabase.auth.sign_in_with_otp()` for phone-based authentication
- OTP verification via `supabase.auth.verify_otp()`
- Users created with email format: `{phone_number}@kangundi.temp`

#### Username + Password Login (Admin Users)

- Uses `supabase.auth.sign_in_with_password()` for admin authentication
- Passwords managed by Supabase (encrypted and secure)
- Admin status stored in `user_metadata.is_admin`

### 3. User Management Functions

#### `get_user_by_phone(phone_number)`

- Queries `auth.users` via `supabase.auth.admin.list_users()`
- Matches on `phone` field or email pattern
- Returns formatted user dict with metadata

#### `get_user_by_username(username)`

- Queries `auth.users` via admin API
- Searches in `user_metadata.username`
- Returns formatted user dict

#### `create_user(name, phone_number, username=None, password=None, is_admin=False)`

- Creates user via `supabase.auth.admin.create_user()`
- Stores custom data in `user_metadata`
- Auto-confirms email for phone-based users

### 4. Session Management

- Session now includes `user_id` from Supabase auth
- Maintains backward compatibility with `phone_number`, `username`, `name`, `is_admin` in session

## Required Supabase Configuration

### 1. Enable Phone Authentication

In Supabase Dashboard → Authentication → Providers:

- Enable Phone provider
- Configure SMS provider (Twilio, MessageBird, etc.) OR use custom MSG91 implementation

### 2. Configure Email Settings

Even though using phone auth, emails are used as identifiers:

- Enable Email provider
- Configure SMTP or use Supabase's default email service

### 3. JWT Settings

Ensure JWT expiration matches Flask session lifetime (default: 1 hour)

### 4. User Metadata Schema

No database schema required - metadata is automatically stored in `auth.users.user_metadata`:

```json
{
  "name": "User Name",
  "phone_number": "+919876543210",
  "username": "admin_user",
  "is_admin": false
}
```

## Migration Steps

### For Existing Users in Custom Table:

If you have existing users in a `users` table, migrate them to `auth.users`:

```python
# Migration script (run once)
from supabase import create_client
import os

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Fetch all users from old table
old_users = supabase.table('users').select('*').execute().data

for user in old_users:
    try:
        # Create in auth.users
        supabase.auth.admin.create_user({
            'email': f"{user['phone_number']}@kangundi.temp",
            'phone': user['phone_number'],
            'user_metadata': {
                'name': user['name'],
                'phone_number': user['phone_number'],
                'username': user.get('username'),
                'is_admin': user.get('is_admin', False)
            },
            'email_confirm': True
        })
        print(f"✓ Migrated: {user['phone_number']}")
    except Exception as e:
        print(f"✗ Failed to migrate {user['phone_number']}: {e}")

# After successful migration, you can drop the old users table
```

## Testing

### Test Phone OTP Login:

1. Navigate to `/signup`
2. Enter name and phone number
3. Receive OTP (via MSG91 or console log)
4. Verify OTP to create account
5. Login with phone + OTP

### Test Admin Login:

1. Create admin user via script or Supabase Dashboard
2. Login with username + password
3. Verify admin dashboard access

## Environment Variables

No changes to `.env` file required - same variables are used:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_or_service_key
MSG91_AUTH_KEY=your_msg91_key
MSG91_TEMPLATE_ID=your_template_id
MSG91_SENDER_ID=KANGND
SECRET_KEY=your_flask_secret_key
```

## Benefits of Migration

1. **Security**: Passwords managed by Supabase (bcrypt encryption)
2. **Scalability**: Built-in rate limiting and security features
3. **Maintenance**: No custom user table schema to maintain
4. **Features**: Access to Supabase auth features (MFA, social login, etc.)
5. **Compliance**: Supabase handles auth compliance and best practices

## Rollback Plan

If needed to rollback to custom table:

1. Keep old `users` table (don't drop)
2. Revert to previous `app.py` version
3. Users will need to re-signup or migrate back

## Notes

- Phone numbers stored as `+91XXXXXXXXXX` format
- Email placeholder format: `{phone}@kangundi.temp` (not used for communication)
- OTP still sent via MSG91 (not Supabase SMS provider)
- Admin users can still use username+password login
