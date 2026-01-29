from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from functools import wraps
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import qrcode
from urllib.parse import quote_plus
import random
import string
import requests
import hmac
import hashlib
import json
# --- UPI Payment Confirmation Route ---
from markupsafe import Markup


# --- UPI QR Payment Helpers ---
def generate_upi_link(upi_id, merchant_name, amount, note):
    """
    Generate a UPI payment link.
    """
    params = {
        'pa': upi_id,
        'pn': merchant_name,
        'am': str(amount),
        'cu': 'INR',
        'tn': note
    }
    # URL encode values
    param_str = '&'.join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
    return f"upi://pay?{param_str}"

def generate_qr_code(data, booking_id):
    """
    Generate a QR code image for the given data and save it under static/qr/.
    Returns the relative path to the QR image.
    """
    qr_dir = os.path.join('static', 'qr')
    os.makedirs(qr_dir, exist_ok=True)
    filename = f"upi_qr_{booking_id}.png"
    filepath = os.path.join(qr_dir, filename)
    img = qrcode.make(data)
    img.save(filepath)
    return f"/static/qr/{filename}"

# In-memory store for UTRs (for demo)
utr_store = {}

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Session configuration - 1 hour timeout
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Refresh session on each request (rolling timeout)

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(supabase_url, supabase_key)

# Cashfree configuration
CASHFREE_APP_ID = os.getenv('CASHFREE_APP_ID', '')
CASHFREE_SECRET_KEY = os.getenv('CASHFREE_SECRET_KEY', '')
CASHFREE_BASE_URL = os.getenv('CASHFREE_BASE_URL', 'https://sandbox.cashfree.com')

# Service-role client for trusted writes (never expose key to frontend)
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
supabase_sr: Client = create_client(supabase_url, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else supabase



# Flask-Mail configuration for Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'kangundihomestay@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'kangundihomestay@gmail.com')

mail = Mail(app)

# Helper functions for database operations

def get_user_by_email(email):
    """Get user by email"""
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
    # Make get_or_create_payment_id available in Jinja templates (must be after function definition)
    app.jinja_env.globals['get_or_create_payment_id'] = get_or_create_payment_id

    return None

def get_user_by_username(username):
    """Get user by username"""
    try:
        response = supabase.table('users').select('*').eq('username', username).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting user by username: {e}")
        return None


def create_user(name, email, username=None, password_hash=None, is_admin=False):
    """Create a new user in database. For OTP users we still populate username to satisfy DB constraints."""
    try:
        username_to_save = username or email  # keep unique/required column satisfied
        password_hash_to_save = password_hash or ''  # some schemas require non-null
        response = supabase.table('users').insert({
            'name': name,
            'email': email,
            'username': username_to_save,
            'password_hash': password_hash_to_save,
            'is_admin': is_admin
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))



def send_otp_via_email(email, otp):
    """Send OTP to user via email using Flask-Mail."""
    try:
        subject = "Your Kangundi HomeStay OTP"
        body = f"Your OTP for login/signup is: {otp}\n\nIf you did not request this, please ignore."
        msg = Message(subject=subject, recipients=[email], body=body)
        mail.send(msg)
        print(f"Sent OTP {otp} to email: {email}")
        return True
    except Exception as e:
        print(f"Error sending OTP via email: {e}")
        return False


def get_homestay_by_id(homestay_id):
    """Fetch a single homestay by id."""
    try:
        response = supabase.table('homestays').select('*').eq('id', homestay_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching homestay by id: {e}")
        return None


def create_booking(booking_data):
    """Insert a booking record; returns inserted booking or None on failure."""
    try:
        response = supabase.table('bookings').insert(booking_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        error_msg = str(e)
        print(f"Error creating booking: {e}")
        
        # If error is about missing column, try to find which column and retry without it
        if "Could not find the" in error_msg and "column of 'bookings'" in error_msg:
            # Extract column name from error message
            import re
            match = re.search(r"Could not find the '(\w+)' column", error_msg)
            if match:
                missing_col = match.group(1)
                print(f"⚠️  Column '{missing_col}' not found in bookings table.")
                print(f"   Please add it to Supabase or the field will be skipped.")
                
                # Remove the problematic column and retry
                if missing_col in booking_data:
                    booking_data_filtered = {k: v for k, v in booking_data.items() if k != missing_col}
                    try:
                        response = supabase.table('bookings').insert(booking_data_filtered).execute()
                        return response.data[0] if response.data else None
                    except Exception as e2:
                        print(f"Error creating booking (retry): {e2}")
                        return None
        
        return None


def get_booking_by_id(booking_id):
    """Fetch booking by id."""
    try:
        response = supabase.table('bookings').select('*').eq('id', booking_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching booking: {e}")
        return None


def compute_nights(from_date_str, till_date_str):
    """Return positive night count or None if invalid."""
    try:
        start = datetime.fromisoformat(from_date_str)
        end = datetime.fromisoformat(till_date_str)
    except Exception:
        return None
    delta = int((end - start).days)
    print(f"DEBUG compute_nights: from={from_date_str}, till={till_date_str}, delta={delta} (type: {type(delta).__name__})")
    return delta if delta > 0 else None


# Cashfree helpers
def create_cashfree_order(order_id: str, amount: float, customer_id: str, phone: str, return_url: str = None):
    """Create a Cashfree order and return payment_session_id."""
    if not all([CASHFREE_APP_ID, CASHFREE_SECRET_KEY, CASHFREE_BASE_URL]):
        raise RuntimeError("Cashfree environment variables missing")

    # Use correct endpoint for API v2023-08-01
    url = f"{CASHFREE_BASE_URL}/pg/orders"
    headers = {
        "Content-Type": "application/json",
        "x-client-id": CASHFREE_APP_ID,
        "x-client-secret": CASHFREE_SECRET_KEY,
        "x-api-version": "2023-08-01",
    }
    
    # Build payload with required fields
    payload = {
        "order_id": order_id,
        "order_amount": float(amount),
        "order_currency": "INR",
        "customer_details": {
            "customer_id": str(customer_id),
            "customer_phone": str(phone),
        },
    }
    
    # Add return_url if provided (for redirect flow)
    if return_url:
        payload["order_meta"] = {"return_url": return_url}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception as exc:  # network or timeout
        raise RuntimeError(f"Cashfree order request failed: {exc}")

    if resp.status_code >= 300:
        raise RuntimeError(f"Cashfree order error: {resp.status_code} {resp.text}")

    data = resp.json()
    payment_session_id = data.get("payment_session_id")
    if not payment_session_id:
        raise RuntimeError("Cashfree response missing payment_session_id")
    return payment_session_id


def verify_cashfree_signature(raw_body: str, signature: str) -> bool:
    """Verify webhook signature using HMAC-SHA256."""
    if not CASHFREE_SECRET_KEY or not signature:
        return False
    computed = hmac.new(
        CASHFREE_SECRET_KEY.encode("utf-8"),
        raw_body.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)

def get_booked_beds_for_date_range(homestay_id, from_date_str, till_date_str):
    """Get total number of booked beds for a date range, counting beds booked in overlapping bookings."""
    try:
        from_date = datetime.fromisoformat(from_date_str).date()
        till_date = datetime.fromisoformat(till_date_str).date()
        
        # Get all confirmed/paid bookings for this homestay
        response = supabase.table('bookings').select('*').eq('homestay_id', homestay_id).in_('status', ['paid', 'confirmed']).execute()
        
        if not response.data:
            return 0
        
        total_booked_beds = 0
        for booking in response.data:
            try:
                booking_from = datetime.fromisoformat(booking['from_date']).date()
                booking_till = datetime.fromisoformat(booking['till_date']).date()
                beds_booked = booking.get('beds_booked', 1)  # Default to 1 bed if not specified
                
                # Check if booking overlaps with requested date range
                if booking_from < till_date and booking_till > from_date:
                    total_booked_beds += beds_booked
            except Exception:
                continue
        
        return total_booked_beds
    except Exception as e:
        print(f"Error calculating booked beds: {e}")
        return 0

def get_available_beds_for_dates(homestay_id, from_date_str, till_date_str):
    """Get available beds for a date range."""
    try:
        homestay = get_homestay_by_id(homestay_id)
        if not homestay:
            return 0
        
        total_beds = homestay.get('beds', 0) or 0
        booked_beds = get_booked_beds_for_date_range(homestay_id, from_date_str, till_date_str)
        available = max(0, total_beds - booked_beds)
        
        return available
    except Exception as e:
        print(f"Error getting available beds: {e}")
        return 0

def get_availability_status(homestay_id, days=7):
    """Get availability status for next N days."""
    try:
        homestay = get_homestay_by_id(homestay_id)
        if not homestay:
            return {}
        
        total_beds = homestay.get('beds', 0) or 0
        availability = {}
        
        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).date()
            date_str = date.isoformat()
            next_date_str = (date + timedelta(days=1)).isoformat()
            
            booked = get_booked_beds_for_date_range(homestay_id, date_str, next_date_str)
            available = max(0, total_beds - booked)
            
            availability[date_str] = {
                'available': available,
                'total': total_beds,
                'is_fully_booked': available == 0,
                'booked': booked,
                'day': date.strftime('%d'),
                'month': date.strftime('%b')
            }
        
        return availability
    except Exception as e:
        print(f"Error getting availability status: {e}")
        return {}

def login_required(f):
    """Decorator to protect routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to protect admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check admin status
        is_admin = session.get('is_admin', False)
        if not is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('home'))
        
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/start')
@admin_required
def start():
    """Inauguration landing page - admin only"""
    return render_template('inauguration.html')

@app.route('/inauguration-login', methods=['POST'])
@admin_required
def inauguration_login():
    """Special inauguration login - creates guest session"""
    session.permanent = True
    session['name'] = 'Guest'
    session['phone_number'] = 'guest_user'
    session['is_admin'] = False
    
    flash('Welcome to Kangundi HomeStay Inauguration!', 'success')
    return redirect(url_for('home'))

@app.route('/home')
def home():
    """Home page - shows landing page if not logged in, dashboard if logged in"""
    # If user is logged in, show their dashboard
    if 'user_id' in session:
        user_data = {
            'name': session.get('name', 'User'),
            'phone_number': session.get('phone_number', ''),
            'email': session.get('email', ''),
            'created_at': datetime.now()
        }
        
        return render_template('dashboard.html', user=user_data)
    
    # If not logged in, show public home page
    return render_template('home.html')

@app.route('/about')
def about():
    """About page with detailed Kangundi history"""
    return render_template('about.html')


@app.route('/contact')
def contact():
    """Public contact page."""
    contact_info = {
        'phone': '+91 70759 21367',
        'email': 'stay@kangundi.com',
        'address': 'Kangundi Estate, Kuppam, Andhra Pradesh',
        'hours': '09:00 AM - 08:00 PM IST'
    }
    return render_template('contact.html', contact=contact_info)


@app.route('/terms')
def terms():
    """Terms and Conditions page."""
    last_updated = "27-01-2026 12:20:11"
    return render_template('terms.html', last_updated=last_updated)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Validation
        if not name or not email or not phone_number or not password or not confirm_password:
            flash('All fields are required!', 'error')
            return redirect(url_for('signup'))

        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))

        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address!', 'error')
            return redirect(url_for('signup'))

        try:
            # Check if user already exists in public.users table
            existing = supabase.table('users').select('*').eq('email', email).execute()
            if existing.data:
                flash('This email is already registered! Please login.', 'error')
                return redirect(url_for('login'))

            # Generate and send OTP
            otp = generate_otp()
            session['signup_otp'] = otp
            session['signup_email'] = email
            session['signup_name'] = name
            session['signup_phone'] = phone_number

            if send_otp_via_email(email, otp):
                flash(f'OTP sent to {email}', 'success')
            else:
                flash(f'Failed to send OTP. Your OTP: {otp}', 'info')

            return redirect(url_for('verify_signup_otp'))

        except Exception as e:
            print(f"Signup error: {e}")
            flash(f'Signup error. Please try again.', 'error')

    return render_template('signup.html')

@app.route('/verify-signup-otp', methods=['GET', 'POST'])
def verify_signup_otp():
    if 'signup_otp' not in session:
        flash('Please sign up first!', 'error')
        return redirect(url_for('signup'))

    if request.method == 'POST':
        otp = request.form.get('otp')
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        if otp == session.get('signup_otp'):
            email = session.get('signup_email')
            name = session.get('signup_name')
            phone_number = session.get('signup_phone')
            if not password or not confirm_password:
                flash('Please enter and confirm your password.', 'error')
                return render_template('verify_otp.html', page_type='signup')
            if password != confirm_password:
                flash('Passwords do not match!', 'error')
                return render_template('verify_otp.html', page_type='signup')
            try:
                password_hash = generate_password_hash(password)
                result = supabase.table('users').insert({
                    'email': email,
                    'name': name,
                    'phone_number': phone_number,
                    'password_hash': password_hash,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }).execute()
                if result.data:
                    user = result.data[0]
                    session['user_id'] = user['id']
                    session['phone_number'] = phone_number
                    session['name'] = name
                    session['is_admin'] = user.get('is_admin', False)
                    session.permanent = True
                    
                    session.pop('signup_otp', None)
                    session.pop('signup_phone', None)
                    session.pop('signup_name', None)
                    
                    flash(f'Welcome {name}! Your account has been created.', 'success')
                    
                    # Redirect admin to admin dashboard
                    if session.get('is_admin', False):
                        return redirect(url_for('admin_dashboard'))
                    
                    return redirect(url_for('home'))
            except Exception as e:
                print(f"User creation error: {e}")
                flash('Error creating account. Please try again.', 'error')
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    return render_template('verify_otp.html', page_type='signup')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        login_method = request.form.get('login_method', 'password')
        password = request.form.get('password', '').strip()
        otp = request.form.get('otp', '').strip()

        if not email:
            flash('Please enter your email!', 'error')
            return redirect(url_for('login'))

        user = get_user_by_email(email)
        if not user:
            flash('No account found for this email.', 'error')
            return redirect(url_for('login'))

        if login_method == 'password':
            if not password:
                flash('Please enter your password!', 'error')
                return redirect(url_for('login'))
            if not check_password_hash(user['password_hash'], password):
                flash('Incorrect password.', 'error')
                return redirect(url_for('login'))
            # Successful login
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['name'] = user['name']
            session['phone_number'] = user.get('phone_number', '')
            session['is_admin'] = user.get('is_admin', False)
            session.permanent = True
            flash(f'Welcome back, {user["name"]}!', 'success')
            if session.get('is_admin', False):
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))

        elif login_method == 'otp':
            if not otp:
                flash('Please enter the OTP sent to your email.', 'error')
                return redirect(url_for('login'))
            if otp != session.get('login_otp') or email != session.get('login_otp_email'):
                flash('Invalid OTP.', 'error')
                return redirect(url_for('login'))
            # Successful OTP login
            session['user_id'] = user['id']
            session['email'] = user['email']
            session['name'] = user['name']
            session['phone_number'] = user.get('phone_number', '')
            session['is_admin'] = user.get('is_admin', False)
            session.permanent = True
            session.pop('login_otp', None)
            session.pop('login_otp_email', None)
            flash(f'Welcome back, {user["name"]}!', 'success')
            if session.get('is_admin', False):
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))

        else:
            flash('Invalid login method.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

# Endpoint to request OTP for login
@app.route('/request-login-otp', methods=['POST'])
def request_login_otp():
    data = request.get_json()
    email = data.get('email', '').strip()
    user = get_user_by_email(email)
    if not user:
        return {'message': 'No account found for this email.'}, 404
    otp = generate_otp()
    session['login_otp'] = otp
    session['login_otp_email'] = email
    if send_otp_via_email(email, otp):
        return {'message': f'OTP sent to {email}.'}
    else:
        return {'message': 'Failed to send OTP.'}, 500

@app.route('/verify-login-otp', methods=['GET', 'POST'])
## Remove verify_login_otp route (no longer needed, handled in login)

@app.route('/rooms')
@login_required
def rooms():
    """Display all available homestays"""
    try:
        response = supabase.table('homestays').select('*').execute()
        homestays_data = response.data if response.data else []
    except Exception as e:
        print(f"Error fetching homestays: {e}")
        flash('Error loading homestays. Please try again.', 'error')
        homestays_data = []
    
    user_data = {
        'name': session.get('name', 'User'),
        'phone_number': session.get('phone_number', '')
    }
    
    return render_template('rooms.html', homestays=homestays_data, user=user_data)

@app.route('/homestay/<int:homestay_id>')
@login_required
def homestay_details(homestay_id):
    """Display details of a specific homestay"""
    try:
        response = supabase.table('homestays').select('*').eq('id', homestay_id).execute()
        
        if not response.data or len(response.data) == 0:
            flash('Homestay not found!', 'error')
            return redirect(url_for('rooms'))
        
        homestay = response.data[0]
    except Exception as e:
        print(f"Error fetching homestay: {e}")
        flash('Error loading homestay details. Please try again.', 'error')
        return redirect(url_for('rooms'))
    
    # Get availability status for next 30 days
    availability = get_availability_status(homestay_id, 30)

    # Build calendar-friendly structure (start today, 30 days)
    calendar_days = []
    today = datetime.now().date()
    for i in range(30):
        day_date = today + timedelta(days=i)
        day_str = day_date.isoformat()
        day_info = availability.get(day_str, {})
        calendar_days.append({
            'date': day_str,
            'day': day_info.get('day', day_date.strftime('%d')),
            'month': day_info.get('month', day_date.strftime('%b')),
            'weekday': day_date.weekday(),  # 0 = Monday
            'available': day_info.get('available', 0),
            'total': day_info.get('total', 0),
            'is_fully_booked': day_info.get('is_fully_booked', False),
            'booked': day_info.get('booked', 0)
        })

    calendar_meta = {
        'start_weekday': today.weekday(),
        'month_label': today.strftime('%B %Y')
    }
    
    user_data = {
        'name': session.get('name', 'User'),
        'phone_number': session.get('phone_number', '')
    }
    
    return render_template(
        'homestay_details.html',
        homestay=homestay,
        user=user_data,
        availability=availability,
        calendar_days=calendar_days,
        calendar_meta=calendar_meta,
    )


@app.route('/book/<int:homestay_id>', methods=['GET', 'POST'])
@login_required
def book_homestay(homestay_id):
    """Capture stay dates and stage a booking before payment."""
    homestay = get_homestay_by_id(homestay_id)
    if not homestay:
        flash('Homestay not found.', 'error')
        return redirect(url_for('rooms'))

    if request.method == 'POST':
        from_date = request.form.get('from_date')
        till_date = request.form.get('till_date')
        beds_requested = int(request.form.get('beds_requested', 1))

        if not from_date or not till_date:
            flash('Please select both dates.', 'error')
            return redirect(url_for('book_homestay', homestay_id=homestay_id))

        nights = compute_nights(from_date, till_date)
        if not nights:
            flash('Till date must be after from date.', 'error')
            return redirect(url_for('book_homestay', homestay_id=homestay_id))

        # Check bed availability
        available_beds = get_available_beds_for_dates(homestay_id, from_date, till_date)
        if beds_requested > available_beds:
            flash(f'Only {available_beds} bed(s) available for your selected dates. Homestay has {homestay.get("beds", 0)} total beds.', 'error')
            return redirect(url_for('book_homestay', homestay_id=homestay_id))

        # Price is fixed: ₹500 per bed per night
        price_per_bed_per_night = 500
        # FIX: Explicit calculation - should be 2000 for 2beds*2nights*500
        total_amount = int(nights) * int(beds_requested) * int(price_per_bed_per_night)
        
        # DEBUG LOG
        print(f"DEBUG CALC: nights={nights}, beds={beds_requested}, price={price_per_bed_per_night}, result={total_amount}")

        session['pending_booking'] = {
            'homestay_id': homestay_id,
            'from_date': from_date,
            'till_date': till_date,
            'nights': nights,
            'beds_requested': beds_requested,
            'price_per_bed_per_night': price_per_bed_per_night,
            'total_amount': total_amount,
            'homestay_owner': homestay.get('owner'),
            'homestay_contact': homestay.get('contact'),
            'homestay_image': homestay.get('image'),
        }

        return redirect(url_for('payment'))

    # Get availability info for the form
    availability = get_availability_status(homestay_id, 30)
    
    return render_template('book_homestay.html', homestay=homestay, availability=availability)


@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    """Demo payment step; on success create booking and redirect to receipt."""
    pending = session.get('pending_booking')
    if not pending:
        flash('No booking in progress.', 'error')
        return redirect(url_for('rooms'))
    
    # RECALCULATE total_amount to ensure it's correct
    nights_val = pending.get('nights', 1)
    beds_val = pending.get('beds_requested', 1)
    price_per_bed = 500
    calculated_total = int(nights_val) * int(beds_val) * int(price_per_bed)
    
    # Update the pending dict with the correct total
    pending['total_amount'] = calculated_total
    session['pending_booking'] = pending
    

    homestay = get_homestay_by_id(pending['homestay_id'])

    if request.method == 'POST':
        payment_ref = f"DEMO-{random.randint(100000, 999999)}"
        user_name = session.get('name', 'User')
        booking_payload = {
            'homestay_id': pending['homestay_id'],
            'from_date': pending['from_date'],
            'till_date': pending['till_date'],
            'nights': pending['nights'],
            'beds_booked': pending.get('beds_requested', 1),
            'total_amount': pending['total_amount'],
            'status': 'paid',
            'payment_reference': payment_ref,
            'user_id': session.get('user_id'),
            'user_phone': session.get('phone_number'),
            'user_email': session.get('email'),
            'user_name': user_name,
        }

        booking = create_booking(booking_payload)

        # Clear pending booking regardless of success to avoid duplicate attempts
        session.pop('pending_booking', None)

        if not booking:
            flash('Payment succeeded but booking could not be saved. Please contact support.', 'error')
            return redirect(url_for('rooms'))

        flash('Payment successful! Booking confirmed.', 'success')
        return redirect(url_for('receipt', booking_id=booking['id']))

    return render_template('payment.html', pending=pending, homestay=homestay)


@app.route('/receipt/<booking_id>')
@login_required
def receipt(booking_id):
    """Show booking receipt."""
    booking = get_booking_by_id(booking_id)
    if not booking:
        flash('Booking not found.', 'error')
        return redirect(url_for('rooms'))

    homestay = get_homestay_by_id(booking['homestay_id']) if booking.get('homestay_id') else None
    return render_template('receipt.html', booking=booking, homestay=homestay)


@app.route('/payments/create-order', methods=['POST'])
def create_order():
    """Create a Cashfree order and persist a pending payment row."""
    try:
        payload = request.get_json(force=True)
        order_id = payload.get('order_id')
        amount = float(payload.get('amount', 0))
        customer_id = payload.get('customer_id')
        phone = payload.get('phone')

        if not all([order_id, amount, customer_id, phone]):
            print(f"Missing fields in payment request: {payload}")
            return {"error": "Missing required fields"}, 400
        if amount <= 0:
            return {"error": "Invalid amount"}, 400

        # Generate return URL for redirect after payment
        return_url = url_for('receipt', booking_id='PENDING', _external=True)
        
        payment_session_id = create_cashfree_order(order_id, amount, customer_id, phone, return_url)

        # Store payment as pending
        try:
            supabase_sr.table('payments').insert({
                "order_id": order_id,
                "amount": amount,
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as db_exc:
            print(f"Payments insert error: {db_exc}")
            # Do not fail payment creation if DB write has a transient issue

        return {"payment_session_id": payment_session_id}, 200

    except RuntimeError as e:
        print(f"Create order runtime error: {e}")
        return {"error": str(e)}, 500
    except Exception as e:
        print(f"Create order error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "Could not create order"}, 500


@app.route('/payments/cashfree-webhook', methods=['POST'])
def cashfree_webhook():
    """Handle Cashfree webhooks with signature verification and idempotency."""
    raw_body = request.get_data(as_text=True)
    signature = request.headers.get('x-webhook-signature') or request.headers.get('x-cf-signature')

    if not verify_cashfree_signature(raw_body, signature):
        return {"error": "invalid signature"}, 400

    try:
        evt = json.loads(raw_body)
    except Exception:
        return {"error": "invalid payload"}, 400

    event_type = evt.get('type')
    data = evt.get('data', {})
    order = data.get('order', {})
    order_id = order.get('order_id')

    if not order_id:
        return {"error": "missing order_id"}, 400

    # Idempotency: check existing status
    try:
        existing = supabase_sr.table('payments').select('status').eq('order_id', order_id).limit(1).execute()
        current_status = existing.data[0]['status'] if existing.data else None
        if current_status in ('SUCCESS', 'FAILED'):
            return {"ok": True}, 200
    except Exception as db_exc:
        print(f"Payments fetch error: {db_exc}")
        # Proceed to upsert regardless

    new_status = None
    if event_type == "PAYMENT_SUCCESS_WEBHOOK":
        new_status = "SUCCESS"
    elif event_type == "PAYMENT_FAILED_WEBHOOK":
        new_status = "FAILED"
    else:
        # Acknowledge unhandled events to avoid retries
        return {"ok": True, "ignored": True}, 200

    try:
        supabase_sr.table('payments').upsert({
            "order_id": order_id,
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }, on_conflict="order_id").execute()
    except Exception as db_exc:
        print(f"Payments upsert error: {db_exc}")
        return {"error": "db error"}, 500

    return {"ok": True}, 200


@app.route('/bookings')
@login_required
def bookings():
    """List current user's bookings."""
    user_id = session.get('user_id')
    user_phone = session.get('phone_number')
    user_email = session.get('email')
    user_name = session.get('name', 'User')

    try:
        query = supabase.table('bookings').select('*')
        # Filter by email (most reliable), then phone, then name
        if user_email:
            query = query.eq('user_email', user_email)
        elif user_phone:
            query = query.eq('user_phone', user_phone)
        elif user_name:
            query = query.eq('user_name', user_name)
        
        response = query.order('from_date', desc=False).execute()
        bookings_data = response.data if response.data else []
        
        # Fetch homestay details for each booking
        for booking in bookings_data:
            homestay = get_homestay_by_id(booking['homestay_id']) if booking.get('homestay_id') else None
            if homestay:
                booking['homestay'] = {
                    'owner': homestay.get('owner'),
                    'rooms': homestay.get('rooms'),
                    'beds': homestay.get('beds'),
                    'price': homestay.get('price'),
                    'contact': homestay.get('contact')
                }
    except Exception as e:
        print(f"Error fetching bookings: {e}")
        bookings_data = []
        flash('Could not load bookings right now.', 'error')

    return render_template('bookings.html', bookings=bookings_data, user_name=user_name)

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard to view and manage homestays"""
    try:
        response = supabase.table('homestays').select('*').execute()
        homestays_data = response.data if response.data else []
    except Exception as e:
        print(f"Error fetching homestays: {e}")
        flash('Error loading homestays.', 'error')
        homestays_data = []
    
    # Fetch all bookings for admin
    try:
        response = supabase.table('bookings').select('*').order('from_date', desc=True).execute()
        bookings_data = response.data if response.data else []
        
        # Fetch homestay details for each booking
        for booking in bookings_data:
            homestay = get_homestay_by_id(booking['homestay_id']) if booking.get('homestay_id') else None
            if homestay:
                booking['homestay'] = {
                    'owner': homestay.get('owner'),
                    'rooms': homestay.get('rooms'),
                    'beds': homestay.get('beds'),
                    'price': homestay.get('price'),
                    'contact': homestay.get('contact')
                }
    except Exception as e:
        print(f"Error fetching bookings: {e}")
        bookings_data = []
    
    admin_name = session.get('name', 'Admin')
    return render_template('admin_dashboard.html', homestays=homestays_data, bookings=bookings_data, username=admin_name)

@app.route('/admin/homestay/add', methods=['GET', 'POST'])
@admin_required
def admin_add_homestay():
    """Add a new homestay"""
    if request.method == 'POST':
        try:
            def parse_int_field(val, fallback=0):
                if val is None or val == '':
                    return fallback
                try:
                    return int(val)
                except Exception:
                    return fallback
            homestay_data = {
                'owner': request.form.get('owner'),
                'rooms': parse_int_field(request.form.get('rooms')),
                'beds': parse_int_field(request.form.get('beds')),
                'floor': request.form.get('floor'),
                'description': request.form.get('description'),
                'price': parse_int_field(request.form.get('price')),
                'contact': request.form.get('contact')
            }
            # Remove any fields with empty string values
            homestay_data = {k: v for k, v in homestay_data.items() if v != ''}
            
            response = supabase.table('homestays').insert(homestay_data).execute()
            
            if response.data:
                flash('Homestay added successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Error adding homestay. Please try again.', 'error')
        except Exception as e:
            print(f"Error adding homestay: {e}")
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('admin_add_homestay.html')

@app.route('/admin/homestay/<int:homestay_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_homestay(homestay_id):
    """Edit a homestay"""
    try:
        response = supabase.table('homestays').select('*').eq('id', homestay_id).execute()
        if not response.data:
            flash('Homestay not found!', 'error')
            return redirect(url_for('admin_dashboard'))
        
        homestay = response.data[0]
    except Exception as e:
        print(f"Error fetching homestay: {e}")
        flash('Error loading homestay.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        try:
            def parse_int_field(val, fallback):
                if val is None or val == '':
                    return fallback
                try:
                    return int(val)
                except Exception:
                    return fallback
            update_data = {
                'owner': request.form.get('owner'),
                'rooms': parse_int_field(request.form.get('rooms'), homestay.get('rooms', 0)),
                'beds': parse_int_field(request.form.get('beds'), homestay.get('beds', 0)),
                'floor': request.form.get('floor'),
                'description': request.form.get('description'),
                'price': parse_int_field(request.form.get('price'), homestay.get('price', 0)),
                'contact': request.form.get('contact')
            }
            # Remove any fields with empty string values
            update_data = {k: v for k, v in update_data.items() if v != ''}
            
            response = supabase.table('homestays').update(update_data).eq('id', homestay_id).execute()
            
            if response.data:
                flash('Homestay updated successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Error updating homestay. Please try again.', 'error')
        except Exception as e:
            print(f"Error updating homestay: {e}")
            flash(f'Error: {str(e)}', 'error')
    
    return render_template('admin_edit_homestay.html', homestay=homestay)

@app.route('/admin/homestay/<int:homestay_id>/delete', methods=['POST'])
@admin_required
def admin_delete_homestay(homestay_id):
    """Delete a homestay"""
    try:
        response = supabase.table('homestays').delete().eq('id', homestay_id).execute()
        flash('Homestay deleted successfully!', 'success')
    except Exception as e:
        print(f"Error deleting homestay: {e}")
        flash('Error deleting homestay.', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
@login_required
def logout():
    supabase.auth.sign_out()
    session.clear()
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/test-supabase')
def test_supabase():
    """Test endpoint to verify Supabase connection"""
    try:
        # Test if client is initialized
        if not supabase_url or not supabase_key:
            return f"ERROR: Missing environment variables<br>URL: {supabase_url}<br>KEY: {'*' * 10 if supabase_key else 'MISSING'}"
        
        # Test a simple query
        response = supabase.table('homestays').select('id').limit(1).execute()
        return f"✓ Supabase connected!<br>URL: {supabase_url}<br>KEY: {supabase_key[:20]}...<br>Test query successful"
    except Exception as e:
        return f"✗ Supabase error: {str(e)}"



import uuid

# UPI Payment route using payment_id (can be pre-booking)
@app.route('/pay/<payment_id>', endpoint='pay_booking')
def pay_booking(payment_id):
    if not payment_id:
        return "Payment ID required in URL (e.g. /pay/abc123?amount=500)", 404
    try:
        amount = float(request.args.get('amount', 1500))
    except Exception:
        amount = 1500
    note = f"Payment ID: {payment_id}"
    upi_id = "7075921367@ybl"
    merchant_name = "Kangundi Homestay"
    upi_link = generate_upi_link(upi_id, merchant_name, amount, note)
    qr_path = generate_qr_code(upi_link, payment_id)
    return render_template('payment_upi.html',
                          booking_id=payment_id,
                          amount=amount,
                          upi_link=upi_link,
                          qr_path=qr_path)

# Helper to generate and store a payment_id in session for UPI before booking
def get_or_create_payment_id():
    if 'upi_payment_id' not in session:
        session['upi_payment_id'] = str(uuid.uuid4())
    return session['upi_payment_id']

# Make get_or_create_payment_id available in Jinja templates (after definition)
app.jinja_env.globals['get_or_create_payment_id'] = get_or_create_payment_id

# UPI Payment confirmation route (for entering UTR/Txn ID)
@app.route('/confirm/<booking_id>', methods=['GET', 'POST'], endpoint='confirm_booking')
def confirm_booking(booking_id):
    message = None
    if request.method == 'POST':
        utr = request.form.get('utr', '').strip()
        if not utr:
            message = 'Please enter a valid UTR/Transaction ID.'
        else:
            # Store UTR in in-memory store (for demo; in production, store in DB)
            utr_store[booking_id] = utr
            message = f'Thank you! UTR/Txn ID <b>{utr}</b> received for Booking ID <b>{booking_id}</b>. We will verify and confirm your payment shortly.'
    return render_template('confirm_upi.html', booking_id=booking_id, message=message)
                          
if __name__ == '__main__':
    print("✅ Flask application ready!")
    print("🌐 Access at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
