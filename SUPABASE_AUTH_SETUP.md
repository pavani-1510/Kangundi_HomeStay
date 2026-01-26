# Supabase Authentication Setup Guide

## Error: 403 Forbidden on Signup

If you're getting a **403 Forbidden** error during signup, it means signups are disabled in your Supabase project. Follow these steps to enable them:

---

## Step 1: Enable Email/Phone Authentication

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project: `cbgdsujtwbuzwqcmemfj`
3. Navigate to **Authentication** → **Providers** (left sidebar)

### Enable Email Provider:

- Click on **Email** provider
- Toggle **Enable Email Provider** to ON
- **Confirm emails**: Set to OFF for development (or configure SMTP for production)
- Click **Save**

### Enable Phone Provider (Optional but Recommended):

- Click on **Phone** provider
- Toggle **Enable Phone Provider** to ON
- **Phone OTP**: Set to ON
- Click **Save**

---

## Step 2: Configure Auth Settings

1. Go to **Authentication** → **Settings** (left sidebar under Policies)
2. Under **User Signups**, ensure:
   - ✅ **Enable email signups** is checked
   - ✅ **Enable phone signups** is checked (if using phone)

3. Under **Email Auth**:
   - **Confirm email**: Disable for development (users can signup without email confirmation)
   - **Secure email change**: Enable for production

4. **Save changes**

---

## Step 3: Check Rate Limits

1. Go to **Authentication** → **Rate Limits**
2. Ensure rate limits aren't too restrictive:
   - Signups per hour: At least **30-100**
   - Verify OTP attempts: At least **10-20**

---

## Step 4: Test Configuration

### Test Signup with Email + Password:

```python
# This should now work
response = supabase.auth.sign_up({
    'email': 'test@example.com',
    'password': 'testpass123',
    'phone': '+919876543210',
    'options': {
        'data': {
            'name': 'Test User',
            'phone_number': '+919876543210'
        }
    }
})
```

### Test Phone Signup:

```python
response = supabase.auth.sign_up({
    'phone': '+919876543210',
    'password': 'temppass123',
    'options': {
        'data': {
            'name': 'Test User',
            'phone_number': '+919876543210'
        }
    }
})
```

---

## Common Issues & Solutions

### Issue 1: "Email confirmation required"

**Solution**: Disable email confirmation in Auth settings for development

### Issue 2: "Phone provider not configured"

**Solution**: Enable Phone provider in Authentication → Providers

### Issue 3: "Invalid phone number format"

**Solution**: Use international format: `+91` prefix for Indian numbers

### Issue 4: "Rate limit exceeded"

**Solution**: Increase rate limits in Authentication → Rate Limits

### Issue 5: "User already registered"

**Solution**: Either:

- Login with existing credentials
- Delete user from Authentication → Users table
- Use a different email/phone

---

## Production Checklist

Before going live:

- [ ] Enable email confirmation
- [ ] Configure SMTP for email delivery (Settings → Auth → Email Templates)
- [ ] Configure SMS provider for phone OTP (Twilio, etc.)
- [ ] Set appropriate rate limits
- [ ] Enable password strength requirements
- [ ] Set up MFA (Multi-Factor Authentication) if needed
- [ ] Configure redirect URLs for magic links
- [ ] Set session timeout appropriately

---

## Environment Variables

Ensure your `.env` has:

```env
SUPABASE_URL=https://cbgdsujtwbuzwqcmemfj.supabase.co
SUPABASE_KEY=your_anon_key_here  # Make sure this is the ANON key, not service_role
SECRET_KEY=your_flask_secret
MSG91_AUTH_KEY=your_msg91_key  # For SMS OTP
MSG91_SENDER_ID=KANGND
```

---

## Verification Steps

1. ✅ Signups enabled in Supabase
2. ✅ Email provider enabled
3. ✅ Email confirmation disabled (for dev)
4. ✅ Phone provider enabled (optional)
5. ✅ Using correct ANON key (not service role key)
6. ✅ Rate limits configured

After completing these steps, try signing up again!
