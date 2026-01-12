# Kangundi HomeStay - Flask Authentication App

A fully functional Flask web application with user authentication, featuring signup, login, and dashboard pages.

## Features

✅ **User Registration** - Secure signup with email and password validation  
✅ **User Login** - Authentication with session management  
✅ **Password Security** - Passwords are hashed using Werkzeug  
✅ **Protected Routes** - Dashboard accessible only to authenticated users  
✅ **Flash Messages** - User-friendly feedback for all actions  
✅ **Responsive Design** - Beautiful UI that works on all devices  
✅ **SQLite Database** - Lightweight database for user storage  
✅ **Remember Me** - Optional persistent login sessions

## Project Structure

```
Kangundi_HomeStay/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── run.sh                # Quick start script
├── users.db              # SQLite database (created automatically)
├── templates/            # HTML templates
│   ├── base.html         # Base template with navbar
│   ├── signup.html       # Registration page
│   ├── login.html        # Login page
│   └── dashboard.html    # User dashboard
└── static/
    └── style.css         # Stylesheet
```

## Quick Start

### Option 1: Using the run script (Recommended)

```bash
chmod +x run.sh
./run.sh
```

### Option 2: Manual setup

1. **Create a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

## Access the Application

Open your browser and navigate to:

- **Main URL:** http://localhost:5000
- **Login:** http://localhost:5000/login
- **Signup:** http://localhost:5000/signup
- **Dashboard:** http://localhost:5000/dashboard (requires login)

## Usage Guide

### Creating an Account

1. Navigate to the signup page
2. Enter a unique username
3. Provide a valid email address
4. Create a password (minimum 6 characters)
5. Confirm your password
6. Click "Sign Up"

### Logging In

1. Navigate to the login page
2. Enter your username
3. Enter your password
4. Optionally check "Remember me" for persistent sessions
5. Click "Login"

### Dashboard

After logging in, you'll be redirected to your personal dashboard where you can:

- View your profile information
- See account statistics
- Access quick actions
- Check recent activity

## Security Features

- **Password Hashing:** All passwords are hashed using Werkzeug's security functions
- **Session Management:** Secure session handling with Flask-Login
- **CSRF Protection:** Built-in protection against cross-site request forgery
- **Input Validation:** Server-side validation for all user inputs
- **Protected Routes:** Unauthorized users are redirected to login

## Database Schema

### User Model

| Field         | Type     | Description                |
| ------------- | -------- | -------------------------- |
| id            | Integer  | Primary key                |
| username      | String   | Unique username            |
| email         | String   | Unique email address       |
| password_hash | String   | Hashed password            |
| created_at    | DateTime | Account creation timestamp |

## Customization

### Change Secret Key

For production, update the secret key in `app.py`:

```python
app.config['SECRET_KEY'] = 'your-secure-random-key-here'
```

### Modify Port

To run on a different port, edit `app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

### Update Styling

Modify `static/style.css` to customize the appearance.

## Technologies Used

- **Flask** - Web framework
- **Flask-SQLAlchemy** - ORM for database operations
- **Flask-Login** - User session management
- **Werkzeug** - Password hashing and security
- **SQLite** - Database
- **HTML/CSS** - Frontend

## Requirements

- Python 3.7+
- Flask 3.0.0
- Flask-SQLAlchemy 3.1.1
- Flask-Login 0.6.3
- Werkzeug 3.0.1

## Troubleshooting

### Port Already in Use

If port 5000 is already in use, either:

- Stop the process using that port
- Change the port in `app.py`

### Database Issues

If you encounter database errors, delete `users.db` and restart the application to recreate it.

### Module Not Found

Ensure you've activated the virtual environment and installed dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Future Enhancements

- Password reset functionality
- Email verification
- User profile editing
- Profile pictures
- Admin panel
- OAuth integration (Google, Facebook)
- Two-factor authentication

## License

This project is open source and available for educational purposes.

## Support

For issues or questions, please open an issue in the repository.

---

**Made with ❤️ for Kangundi HomeStay**
