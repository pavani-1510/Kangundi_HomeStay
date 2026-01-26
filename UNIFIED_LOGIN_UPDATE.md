# Unified Login System Update

## Overview

The login system has been redesigned to provide a streamlined, unified experience with a single identifier field and flexible authentication options.

## What Changed

### Frontend (login.html)

**Before**: Separate tabs for "Phone + OTP" and "Username + Password" with different input fields
**After**: Single unified interface with:

- One input field for "Phone Number or Email"
- Toggle between "Login with OTP" and "Login with Password"
- Modern pill-style tab switcher
- Contextual help hints

### Backend (app.py)

**Before**: Separate logic for `login_type='phone'` and `login_type='username'`
**After**: Smart identifier detection:

- Automatically detects if input is email (contains '@') or phone number
- Routes to appropriate user lookup function
- Supports both OTP and password authentication based on user choice

## User Experience Flow

### Option 1: Phone + OTP (Primary Method)

1. User enters phone number (e.g., `+919876543210`)
2. Selects "Login with OTP" (default)
3. Clicks "📱 Send OTP"
4. Receives OTP via SMS (MSG91)
5. Enters OTP on verification page
6. Logged in successfully

### Option 2: Email + OTP (New)

1. User enters email (e.g., `admin@kangundi.com`)
2. Selects "Login with OTP"
3. Clicks "📱 Send OTP"
4. Receives OTP (shown in flash message for dev)
5. Enters OTP on verification page
6. Logged in successfully

### Option 3: Email + Password (Admin)

1. User enters email
2. Switches to "Login with Password"
3. Enters password in revealed field
4. Clicks "🔐 Login"
5. Authenticated via Supabase auth
6. Logged in directly (no OTP step)

## Technical Implementation

### Identifier Detection

```python
identifier = request.form.get('identifier', '').strip()
is_email = '@' in identifier

if is_email:
    user = get_user_by_email(identifier)
else:
    user = get_user_by_phone(identifier)
```

### Login Type Handling

```python
login_type = request.form.get('login_type', 'otp')  # otp or password

if login_type == 'otp':
    # Generate and send OTP
    # Redirect to verification page
else:
    # Verify password with Supabase
    # Direct login
```

### Session Data Stored

For OTP flow:

```python
session['login_otp'] = otp
session['login_identifier'] = identifier
session['login_user'] = user
session['login_is_email'] = is_email
```

For successful login:

```python
session['user_id'] = user.id  # from Supabase
session['phone_number'] = user.phone_number
session['username'] = user.username
session['name'] = user.name
session['is_admin'] = user.is_admin
```

## UI Improvements

### Modern Tab Switcher

- Pill-style design with rounded background
- Active state with white background and shadow
- Smooth transitions between states
- Icons for visual feedback (📱 for OTP, 🔐 for password)

### Form Hints

- Contextual help text under identifier field
- Clear explanation of which method works with what
- Friendly message about OTP delivery

### Responsive Design

- Clean, single-column layout
- Works seamlessly on mobile and desktop
- Progressive disclosure (password field only shown when needed)

## Security Features

1. **Input Validation**: Checks for empty fields before submission
2. **Type Detection**: Automatically determines authentication method
3. **Supabase Integration**: Password authentication handled by Supabase
4. **Session Security**: OTP stored temporarily, cleared after verification
5. **Error Handling**: Clear, user-friendly error messages

## Backend Functions Used

### User Lookup

- `get_user_by_phone(phone_number)` - Queries auth.users by phone
- `get_user_by_email(email)` - Queries auth.users by email
- `get_user_by_username(username)` - Queries auth.users by username (metadata)

### Authentication

- `supabase.auth.sign_in_with_password()` - Direct password login
- `supabase.auth.verify_otp()` - Verify OTP tokens
- `send_otp_via_msg91()` - Send SMS OTP via MSG91

## Testing Checklist

- [ ] Phone number + OTP login
- [ ] Email + OTP login
- [ ] Email + Password login
- [ ] Invalid phone number handling
- [ ] Invalid email handling
- [ ] Wrong password handling
- [ ] Wrong OTP handling
- [ ] Account not found error
- [ ] Tab switching functionality
- [ ] Form validation
- [ ] Mobile responsiveness
- [ ] Admin redirect (for admin users)
- [ ] User redirect (for regular users)

## Benefits

1. **Simplified UX**: One field instead of multiple forms
2. **Flexibility**: Users choose their preferred auth method
3. **Mobile-First**: Phone OTP as default for easy mobile login
4. **Admin-Friendly**: Password option for admin accounts
5. **Future-Proof**: Easy to add social login or other methods
6. **Cleaner Code**: Unified logic instead of branching paths

## Environment Variables (Unchanged)

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_service_key
MSG91_AUTH_KEY=your_msg91_key
MSG91_SENDER_ID=KANGND
SECRET_KEY=your_flask_secret
```

## Backwards Compatibility

- Existing users can still login with phone numbers
- Admin users can still use password authentication
- All existing session handling remains intact
- No database migration required

## Future Enhancements

- Email OTP delivery via SMTP
- Social login (Google, Facebook)
- Remember me functionality
- Forgot password flow
- Magic link login
- Biometric authentication (mobile)
