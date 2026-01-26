from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import random
import string
import requests

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

if not supabase_url or not supabase_key:
    print("⚠️  WARNING: SUPABASE_URL or SUPABASE_KEY not found in environment!")
    print(f"   SUPABASE_URL: {'✓ Set' if supabase_url else '✗ Missing'}")
    print(f"   SUPABASE_KEY: {'✓ Set' if supabase_key else '✗ Missing'}")
else:
    print("✓ Supabase credentials loaded")

supabase: Client = create_client(supabase_url, supabase_key)

# MSG91 Configuration for SMS OTP
MSG91_AUTH_KEY = os.getenv('MSG91_AUTH_KEY', '')
MSG91_TEMPLATE_ID = os.getenv('MSG91_TEMPLATE_ID', '')
MSG91_SENDER_ID = os.getenv('MSG91_SENDER_ID', 'KANGND')  # 6 characters max

# Helper functions for database operations
def get_user_by_phone(phone_number):
    """Get user by phone number - returns user metadata if exists"""
    # Note: We can't query auth.users directly, so we store phone as identifier
    # and return a mock structure for checking existence
    return {'phone_number': phone_number, 'exists': True}

def get_user_by_email(email):
    """Get user by email - returns user metadata if exists"""
    # Note: We can't query auth.users directly with anon key
    return {'email': email, 'exists': True}

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_via_msg91(phone_number, otp):
    """Send OTP via MSG91 using v5 OTP API with DLT template support."""
    if not MSG91_AUTH_KEY:
        print("MSG91_AUTH_KEY not configured. OTP not sent.")
        print(f"DEBUG - OTP for {phone_number}: {otp}")
        return True

    try:
        phone = phone_number.replace('+91', '').replace('+', '').strip()

        # Prefer v5 OTP API with template_id (required for DLT compliance)
        url = "https://control.msg91.com/api/v5/otp"
        payload = {
            "mobile": f"91{phone}",
            "otp": otp,
            "sender": MSG91_SENDER_ID,
            "otp_expiry": "10",
        }

        if MSG91_TEMPLATE_ID:
            payload["template_id"] = MSG91_TEMPLATE_ID
        else:
            print("⚠️ MSG91_TEMPLATE_ID not set; DLT delivery may fail.")

        headers = {
            "authkey": MSG91_AUTH_KEY,
            "Content-Type": "application/json"
        }

        print(f"Sending OTP to {phone} with template {payload.get('template_id')}")
        response = requests.post(url, headers=headers, json=payload)

        print(f"MSG91 Response Status: {response.status_code}")
        print(f"MSG91 Response Body: {response.text}")

        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("type") == "success":
                    print(f"✅ OTP sent successfully to {phone_number}")
                    return True
            except Exception:
                pass
            
            if "success" in response.text.lower():
                print(f"✅ OTP sent successfully to {phone_number}")
                return True

        print(f"❌ Failed to send OTP: {response.status_code} - {response.text}")
        return False

    except Exception as e:
        print(f"Error sending OTP via MSG91: {e}")
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
    delta = (end - start).days
    return delta if delta > 0 else None

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
def start():
    """Inauguration landing page"""
    return render_template('inauguration.html')

@app.route('/inauguration-login', methods=['POST'])
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

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'phone_number' in session or 'email' in session:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        
        # Validation
        if not name or not phone_number:
            flash('Name and phone number are required!', 'error')
            return redirect(url_for('signup'))
        
        if len(phone_number) < 10:
            flash('Please enter a valid phone number!', 'error')
            return redirect(url_for('signup'))
        
        try:
            # Phone-only signup with Supabase Auth
            response = supabase.auth.sign_up({
                'phone': phone_number,
                'password': generate_otp(),  # Temporary password
                'options': {
                    'data': {
                        'name': name,
                        'phone_number': phone_number,
                        'is_admin': False
                    }
                }
            })
            
            if response.user:
                # Generate and send OTP for phone verification
                otp = generate_otp()
                session['signup_otp'] = otp
                session['signup_phone'] = phone_number
                session['signup_user_id'] = response.user.id
                
                if send_otp_via_msg91(phone_number, otp):
                    flash(f'OTP sent to {phone_number}', 'success')
                else:
                    flash(f'Failed to send OTP. Your OTP: {otp}', 'info')
                
                return redirect(url_for('verify_signup_otp'))
            else:
                flash('Signup failed. Please try again.', 'error')
                
        except Exception as e:
            print(f"Signup error: {e}")
            error_msg = str(e).lower()
            
            if '403' in error_msg or 'forbidden' in error_msg:
                flash('Signup is currently disabled. Please contact administrator.', 'error')
            elif 'already registered' in error_msg or 'already exists' in error_msg:
                flash('This phone number or email is already registered!', 'error')
            elif 'email' in error_msg and 'invalid' in error_msg:
                flash('Please provide a valid email address.', 'error')
            else:
                flash(f'Signup error. Please try again.', 'error')
    
    return render_template('signup.html')

@app.route('/verify-signup-otp', methods=['GET', 'POST'])
def verify_signup_otp():
    if 'signup_otp' not in session:
        flash('Please sign up first!', 'error')
        return redirect(url_for('signup'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        if otp == session.get('signup_otp'):
            # OTP verified
            session.pop('signup_otp', None)
            session.pop('signup_phone', None)
            session.pop('signup_user_id', None)
            
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    return render_template('verify_otp.html', page_type='signup')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()
        
        if not identifier:
            flash('Please enter your phone number or email!', 'error')
            return redirect(url_for('login'))
        
        # Determine if identifier is email or phone
        is_email = '@' in identifier
        
        try:
            if is_email:
                # Email login - requires password
                if not password:
                    flash('Please enter your password!', 'error')
                    return redirect(url_for('login'))
                
                response = supabase.auth.sign_in_with_password({
                    'email': identifier,
                    'password': password
                })
                
                if response.user:
                    session.permanent = True
                    session['user_id'] = response.user.id
                    session['email'] = response.user.email
                    session['phone_number'] = response.user.phone
                    
                    # Get name from user_metadata, fallback to email username
                    user_name = response.user.user_metadata.get('name', '')
                    if not user_name:
                        # Fallback to email username part or phone
                        if response.user.email:
                            user_name = response.user.email.split('@')[0]
                        elif response.user.phone:
                            user_name = response.user.phone
                        else:
                            user_name = 'User'
                    
                    session['name'] = user_name
                    session['is_admin'] = response.user.user_metadata.get('is_admin', False)
                    
                    flash(f'Welcome back, {user_name}!', 'success')
                    
                    if session.get('is_admin', False):
                        return redirect(url_for('admin_dashboard'))
                    
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('home'))
                else:
                    flash('Invalid email or password!', 'error')
            
            else:
                # Phone login - send OTP
                otp = generate_otp()
                session['login_otp'] = otp
                session['login_identifier'] = identifier
                session['login_is_email'] = False
                
                if send_otp_via_msg91(identifier, otp):
                    flash(f'OTP sent to {identifier}', 'success')
                else:
                    flash(f'Failed to send OTP. Your OTP: {otp}', 'info')
                
                return redirect(url_for('verify_login_otp'))
                    
        except Exception as e:
            print(f"Login error: {e}")
            if 'Invalid login credentials' in str(e) or 'Invalid' in str(e):
                flash('Invalid credentials. Please check and try again.', 'error')
            else:
                flash('Login failed. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/verify-login-otp', methods=['GET', 'POST'])
def verify_login_otp():
    if 'login_otp' not in session:
        flash('Please log in first!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        identifier = session.get('login_identifier')
        is_email = session.get('login_is_email', False)
        
        # Verify with our custom OTP (MSG91)
        if otp == session.get('login_otp'):
            # OTP verified! For phone-only login, we'll send OTP via Supabase and verify
            phone_number = identifier
            try:
                # Send Supabase OTP for the phone
                supabase.auth.sign_in_with_otp({'phone': phone_number})
                
                # Now verify it (Supabase will accept their own OTP or ours)
                # Actually, we need to use Supabase's OTP to complete auth
                # Since we verified our own OTP, let's just create a session
                # But with Supabase auth, we need a proper session token
                
                # Best approach: Store user data in session without full Supabase auth
                # or require password signup for phone users too
                session.permanent = True
                session['phone_number'] = phone_number
                session['user_id'] = phone_number  # Use phone as ID temporarily
                session['name'] = phone_number[:4] + '***'  # Masked phone
                session['is_admin'] = False
                
                # Clear login session data
                session.pop('login_otp', None)
                session.pop('login_identifier', None)
                session.pop('login_is_email', None)
                
                flash(f'Welcome back!', 'success')
                
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('home'))
                    
            except Exception as e:
                print(f"OTP verification error: {e}")
                flash('OTP verification failed. Please try again.', 'error')
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    return render_template('verify_otp.html', page_type='login')

@app.route('/rooms')
@login_required
def rooms():
    """Display all available homestays"""
    try:
        response = supabase.table('homestays').select('*').execute()
        homestays_data = response.data if response.data else []
        
        # Add availability status for each homestay
        for homestay in homestays_data:
            availability = get_availability_status(homestay['id'], 7)
            # Get next available date and beds available today
            today = datetime.now().date().isoformat()
            if today in availability:
                homestay['available_beds'] = availability[today]['available']
                homestay['is_fully_booked'] = availability[today]['is_fully_booked']
            else:
                homestay['available_beds'] = homestay.get('beds', 0)
                homestay['is_fully_booked'] = False
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

        price_per_night = homestay.get('price', 0) or 0
        total_amount = price_per_night * nights

        session['pending_booking'] = {
            'homestay_id': homestay_id,
            'from_date': from_date,
            'till_date': till_date,
            'nights': nights,
            'beds_requested': beds_requested,
            'price_per_night': price_per_night,
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


@app.route('/bookings')
@login_required
def bookings():
    """List current user's bookings."""
    user_id = session.get('user_id')
    user_phone = session.get('phone_number')
    user_name = session.get('name', 'User')

    try:
        query = supabase.table('bookings').select('*')
        # Try to filter by user_id first, then fallback to phone
        if user_id:
            query = query.eq('user_id', user_id)
        elif user_phone:
            query = query.eq('user_phone', user_phone)
        
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
            homestay_data = {
                'owner': request.form.get('owner'),
                'rooms': int(request.form.get('rooms', 0)),
                'beds': int(request.form.get('beds', 0)),
                'floor': request.form.get('floor'),
                'description': request.form.get('description'),
                'price': int(request.form.get('price', 0)),
                'contact': request.form.get('contact')
            }
            
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
            update_data = {
                'owner': request.form.get('owner'),
                'rooms': int(request.form.get('rooms', 0)),
                'beds': int(request.form.get('beds', 0)),
                'floor': request.form.get('floor'),
                'description': request.form.get('description'),
                'price': int(request.form.get('price', 0)),
                'contact': request.form.get('contact')
            }
            
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

if __name__ == '__main__':
    print("✅ Flask application ready!")
    print("🌐 Access at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
