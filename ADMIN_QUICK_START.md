# 🚀 Quick Start - Admin Feature

## ⚡ 3-Step Setup

### Step 1️⃣: Run Database Schema
Go to Supabase → SQL Editor → New Query → Copy-paste from `database_schema.sql` → Run

### Step 2️⃣: Start Your App
```bash
cd /home/pavani/Pavani/VSCODE/Kangundi_HomeStay
source venv/bin/activate
python app.py
```

### Step 3️⃣: Login as Admin
- URL: `http://localhost:5000/login`
- Username: **`admin`**
- Password: **`admin123`**

## ✅ You're Done!

You now have:
- ✅ Admin Dashboard at `/admin/dashboard`
- ✅ Add Homestay form
- ✅ Edit Homestay form  
- ✅ Delete Homestay feature
- ✅ Regular users cannot access admin features

## 🎯 What Admin Can Do

| Action | URL | Access |
|--------|-----|--------|
| View Dashboard | `/admin/dashboard` | Admin only |
| Add Property | `/admin/homestay/add` | Admin only |
| Edit Property | `/admin/homestay/<id>/edit` | Admin only |
| Delete Property | `/admin/homestay/<id>/delete` | Admin only |

## 🔑 Login Credentials

```
Username: admin
Password: admin123
```

## 📋 Form Fields When Adding/Editing

Required:
- Name, Owner, Rooms, Beds, Price, Rating, Image, Features, Description, Contact

Optional:
- Floor, Reviews, Additional Images

## 🛠️ Troubleshooting

**"Could not find table"** → Run database_schema.sql

**Admin login fails** → Check password hash in database_schema.sql

**Can't see admin dashboard** → Make sure `is_admin = TRUE` for admin user

## 📚 Full Documentation

See `ADMIN_FEATURE.md` for complete details and `ADMIN_IMPLEMENTATION.md` for technical info.

## 🎉 Ready to Go!

Your admin system is complete. Start adding and managing homestays!
