# Admin Feature Setup Guide

## 🔐 Admin Login Credentials

Once the database schema is set up, you can login as admin with:

- **Username**: `admin`
- **Password**: `admin123`

## 📋 What is Included

The admin feature provides a complete management system for homestays:

### 1. **Admin Dashboard** (`/admin/dashboard`)
   - View all homestays in a professional table format
   - Statistics showing total homestays and admin user
   - Quick access to edit or delete any homestay

### 2. **Add Homestay** (`/admin/homestay/add`)
   - Form to add new homestay listings
   - Fields for:
     - Name, Owner name
     - Rooms, Beds, Floor
     - Price, Rating, Number of reviews
     - Main image URL and additional image URLs
     - Features (comma-separated)
     - Description and contact

### 3. **Edit Homestay** (`/admin/homestay/<id>/edit`)
   - Full form to update existing homestay details
   - All fields are editable
   - Changes saved immediately to database

### 4. **Delete Homestay** (`/admin/homestay/<id>/delete`)
   - One-click delete with confirmation
   - Removed from database permanently

## 🚀 How to Use

### Step 1: Run the Database Schema

Go to your Supabase SQL Editor and run the contents of `database_schema.sql`:

```sql
-- The file includes:
-- - CREATE TABLE users with is_admin field
-- - CREATE TABLE homestays
-- - INSERT admin user
-- - INSERT 6 sample homestays
```

### Step 2: Login as Admin

1. Go to `http://localhost:5000/login`
2. Enter:
   - Username: `admin`
   - Password: `admin123`
3. You'll be redirected to the **Admin Dashboard**

### Step 3: Manage Homestays

From the admin dashboard, you can:

- **View All Homestays**: See a table with all properties
- **Add New**: Click "Add Homestay" button to add new listings
- **Edit**: Click "Edit" button next to any property
- **Delete**: Click "Delete" button (with confirmation)

## 📝 Database Schema Updates

The `users` table now includes:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,  -- NEW FIELD
    created_at TIMESTAMP
)
```

Regular users created via signup will have `is_admin = FALSE`

## 🔑 Admin vs Regular Users

| Feature | Admin | Regular User |
|---------|-------|--------------|
| Login | ✅ Yes | ✅ Yes |
| View Homestays | ✅ Yes | ✅ Yes |
| Add Homestays | ✅ Yes | ❌ No |
| Edit Homestays | ✅ Yes | ❌ No |
| Delete Homestays | ✅ Yes | ❌ No |
| Access Admin Dashboard | ✅ Yes | ❌ No |
| Dashboard | Admin Panel | User Dashboard |

## 🛡️ Security

- Admin check is enforced in the `@admin_required` decorator
- All admin routes check `is_admin` field in database
- Unauthorized access redirects to user dashboard with error message
- Session stores `is_admin` for quick permission checks

## 📂 New Files Created

- `templates/admin_dashboard.html` - Admin dashboard view
- `templates/admin_add_homestay.html` - Add homestay form
- `templates/admin_edit_homestay.html` - Edit homestay form

## 🔄 How It Works

1. **Login**: Admin and regular users use the same login page
2. **Role Check**: After authentication, `is_admin` field is checked
3. **Route Protection**: `@admin_required` decorator protects admin routes
4. **Database Operations**: All CRUD operations go directly to Supabase
5. **Redirect**: Admins → Admin Dashboard, Users → User Dashboard

## ✨ Features

- **Real-time updates**: Changes save immediately to Supabase
- **Responsive design**: Works on desktop and mobile
- **Error handling**: Graceful error messages for all operations
- **Confirmation dialogs**: Delete operations require confirmation
- **Input validation**: Forms validate required fields

## 🚨 Troubleshooting

**Q: Admin login not working**
A: Make sure you ran the database_schema.sql and the admin user was inserted

**Q: Can't access admin dashboard after login**
A: Check that `is_admin = TRUE` in the users table for the admin user

**Q: Changes not saving**
A: Check your Supabase URL and API key in `.env` file

**Q: Regular user can see admin routes**
A: Check that the `is_admin` field is FALSE for that user in the database

## 🔐 Changing Admin Password

To change the admin password, generate a new hash and update it in Supabase:

```bash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('new_password'))"
```

Then update the admin user in Supabase:

```sql
UPDATE users SET password_hash = 'new_hash' WHERE username = 'admin';
```

## 📞 Next Steps

- Add more properties through the admin panel
- Create additional admin accounts (update database directly)
- Add image upload functionality (future feature)
- Add booking management (future feature)
