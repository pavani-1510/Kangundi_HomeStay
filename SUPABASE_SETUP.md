# Supabase Setup Guide

This guide will walk you through setting up Supabase for your Kangundi HomeStay application.

## Prerequisites

- Python 3.x installed
- Pip package manager
- Internet connection

## Step 1: Install Required Packages

Navigate to your project directory and install the dependencies:

```bash
cd /home/pavani/Pavani/VSCODE/Kangundi_HomeStay
pip install -r requirements.txt
```

## Step 2: Create a Supabase Account

1. Go to [https://supabase.com](https://supabase.com)
2. Click "Start your project" or "Sign Up"
3. Sign up with your email or GitHub account
4. Verify your email if required

## Step 3: Create a New Project

1. After logging in, click "New Project"
2. Fill in the project details:
   - **Name**: `kangundi-homestay` (or any name you prefer)
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose the closest region to your location (India - South Asia for best performance)
   - **Pricing Plan**: Select "Free" (sufficient for development and small apps)
3. Click "Create new project"
4. Wait 2-3 minutes for the project to be provisioned

## Step 4: Get Your API Credentials

1. Once your project is ready, go to **Project Settings** (gear icon in the left sidebar)
2. Click on **API** in the settings menu
3. You'll see two important values:
   - **Project URL**: Something like `https://xxxxxxxxxxxxx.supabase.co`
   - **anon public key**: A long string starting with `eyJ...`
4. Keep this page open - you'll need these values

## Step 5: Create Your Environment File

1. In your project directory, copy the example file:

   ```bash
   cp .env.example .env
   ```

2. Open the `.env` file and fill in your credentials:

   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your_anon_public_key_here
   SECRET_KEY=generate_a_random_secret_key_here
   ```

3. For the SECRET_KEY, you can generate one using Python:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

## Step 6: Set Up Database Tables

1. In your Supabase dashboard, click on **SQL Editor** (database icon with "SQL" in the left sidebar)
2. Click **+ New query**
3. Copy the entire contents of `database_schema.sql` from your project
4. Paste it into the SQL editor
5. Click **Run** (or press Ctrl+Enter)
6. You should see "Success. No rows returned" - this means your tables are created!

## Step 7: Verify Your Setup

Check that your tables were created:

1. Click on **Table Editor** (table icon in the left sidebar)
2. You should see two tables:
   - `users` - For storing user accounts
   - `homestays` - For storing property listings (with 6 sample homestays already inserted)

## Step 8: Test Your Application

1. Start your Flask application:

   ```bash
   python app.py
   ```

2. Open your browser and go to: `http://localhost:5000`

3. Try creating a new account:

   - Go to signup page
   - Create a test account
   - Login with your credentials

4. After logging in, click "Browse Rooms" to see the homestays loaded from Supabase!

## Troubleshooting

### Error: "No module named 'supabase'"

**Solution**: Run `pip install -r requirements.txt`

### Error: "SUPABASE_URL is None"

**Solution**: Make sure your `.env` file exists and has the correct values. Check that there are no spaces around the `=` sign.

### Error: "relation 'users' does not exist"

**Solution**: You need to run the SQL schema. Go back to Step 6 and run the `database_schema.sql` file.

### Can't see homestays on the /rooms page

**Solution**:

1. Go to Supabase Table Editor
2. Check that the `homestays` table has 6 rows
3. If not, rerun the INSERT statements from `database_schema.sql`

### Authentication not working

**Solution**:

1. Check that your `.env` file is in the correct location (same directory as app.py)
2. Verify your SUPABASE_URL and SUPABASE_KEY are correct
3. Make sure the `users` table exists in Supabase

## Security Notes

⚠️ **Important**:

- Never commit your `.env` file to git (it's already in `.gitignore`)
- Keep your database password and API keys secure
- The `anon` key is safe to use in client-side code, but keep your service role key private
- For production, consider using environment variables instead of `.env` files

## Next Steps

Now that your database is set up, you can:

- Add more homestays through the Supabase Table Editor
- Implement booking functionality
- Add reviews and ratings
- Upload real images for your homestays

## Support

If you encounter any issues:

1. Check the Supabase documentation: [https://supabase.com/docs](https://supabase.com/docs)
2. Review your Flask console for error messages
3. Check the browser console for any JavaScript errors
4. Verify your `.env` configuration

Congratulations! Your Kangundi HomeStay app is now using Supabase! 🎉
