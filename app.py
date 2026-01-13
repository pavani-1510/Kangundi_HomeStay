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

supabase: Client = create_client(supabase_url, supabase_key)

# MSG91 Configuration for SMS OTP
MSG91_AUTH_KEY = os.getenv('MSG91_AUTH_KEY', '')
MSG91_TEMPLATE_ID = os.getenv('MSG91_TEMPLATE_ID', '')
MSG91_SENDER_ID = os.getenv('MSG91_SENDER_ID', 'KANGND')  # 6 characters max

# Helper functions for database operations
def get_user_by_phone(phone_number):
    """Get user by phone number"""
    try:
        response = supabase.table('users').select('*').eq('phone_number', phone_number).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting user by phone: {e}")
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

def create_user(name, phone_number, username=None, password_hash=None, is_admin=False):
    """Create a new user in database. For OTP users we still populate username to satisfy DB constraints."""
    try:
        username_to_save = username or phone_number  # keep unique/required column satisfied
        password_hash_to_save = password_hash or ''  # some schemas require non-null
        response = supabase.table('users').insert({
            'name': name,
            'phone_number': phone_number,
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


def send_otp_via_msg91(phone_number, otp):
    """Send OTP via MSG91 SMS"""
    if not MSG91_AUTH_KEY:
        print("MSG91_AUTH_KEY not configured. OTP not sent.")
        print(f"DEBUG - OTP for {phone_number}: {otp}")
        return True  # Return True for testing without API key
    
    try:
        # Remove +91 if present and ensure 10 digits
        phone = phone_number.replace('+91', '').replace('+', '').strip()
        
        # Custom message
        message = f"Your otp to login to Kangundi Homestay is {otp}. Please ignore if this is not by you."
        
        # MSG91 SMS API endpoint (using sendhttp.php for custom messages)
        url = "https://control.msg91.com/api/sendhttp.php"
        
        params = {
            "authkey": MSG91_AUTH_KEY,
            "mobiles": f"91{phone}",
            "sender": MSG91_SENDER_ID,
            "route": "1",  # Promotional route (works for DND numbers)
            "country": "91",
            "message": message
        }
        
        print(f"Sending OTP to {phone} with sender ID: {MSG91_SENDER_ID}")
        print(f"Request params: {params}")
        
        response = requests.get(url, params=params)
        
        print(f"MSG91 Response Status: {response.status_code}")
        print(f"MSG91 Response Body: {response.text}")
        
        # MSG91 returns message ID on success (hex encoded) or error text on failure
        # Check for error keywords instead
        error_keywords = ["error", "invalid", "failure", "failed", "unauthorized", "denied"]
        response_lower = response.text.lower()
        
        if response.status_code == 200 and not any(keyword in response_lower for keyword in error_keywords):
            print(f"✅ OTP sent successfully to {phone_number} (Message ID: {response.text})")
            return True
        else:
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
        print(f"Error creating booking: {e}")
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

def login_required(f):
    """Decorator to protect routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'phone_number' not in session and 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to protect admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session and 'phone_number' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check admin status
        is_admin = session.get('is_admin', False)
        if not is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'phone_number' in session or 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'phone_number' in session or 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        
        # Validation
        if not name or not phone_number:
            flash('All fields are required!', 'error')
            return redirect(url_for('signup'))
        
        if len(phone_number) < 10:
            flash('Please enter a valid phone number!', 'error')
            return redirect(url_for('signup'))
        
        # Check if user already exists
        if get_user_by_phone(phone_number):
            flash('Phone number already registered!', 'error')
            return redirect(url_for('signup'))
        
        # Generate OTP and store in session
        otp = generate_otp()
        session['signup_otp'] = otp
        session['signup_name'] = name
        session['signup_phone'] = phone_number
        
        # Send OTP via MSG91
        if send_otp_via_msg91(phone_number, otp):
            flash(f'OTP sent to {phone_number}', 'success')
        else:
            flash(f'Failed to send OTP. Your OTP: {otp}', 'info')
        
        return redirect(url_for('verify_signup_otp'))
    
    return render_template('signup.html')

@app.route('/verify-signup-otp', methods=['GET', 'POST'])
def verify_signup_otp():
    if 'signup_otp' not in session:
        flash('Please sign up first!', 'error')
        return redirect(url_for('signup'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        if otp == session.get('signup_otp'):
            # OTP verified - create user
            user = create_user(
                session['signup_name'],
                session['signup_phone']
            )
            
            if user:
                # Clear signup session data
                session.pop('signup_otp', None)
                session.pop('signup_name', None)
                session.pop('signup_phone', None)
                
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('An error occurred. Please try again.', 'error')
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    return render_template('verify_otp.html', page_type='signup')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'phone_number' in session or 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        login_type = request.form.get('login_type', 'phone')  # phone or username
        
        if login_type == 'phone':
            # Phone + OTP login
            phone_number = request.form.get('phone_number')
            
            if not phone_number:
                flash('Please enter your phone number!', 'error')
                return redirect(url_for('login'))
            
            user = get_user_by_phone(phone_number)
            
            if user:
                # Generate OTP and store in session
                otp = generate_otp()
                session['login_otp'] = otp
                session['login_phone'] = phone_number
                session['login_user'] = user
                
                # Send OTP via MSG91
                if send_otp_via_msg91(phone_number, otp):
                    flash(f'OTP sent to {phone_number}', 'success')
                else:
                    flash(f'Failed to send OTP. Your OTP: {otp}', 'info')
                
                return redirect(url_for('verify_login_otp'))
            else:
                flash('Phone number not registered! Please sign up.', 'error')
                return redirect(url_for('login'))
        
        else:
            # Username + Password login (for admin)
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('Please enter username and password!', 'error')
                return redirect(url_for('login'))
            
            user = get_user_by_username(username)
            
            if user and user.get('password_hash') and check_password_hash(user['password_hash'], password):
                session.permanent = True
                session['username'] = username
                session['name'] = user['name']
                session['is_admin'] = user.get('is_admin', False)
                
                flash(f'Welcome back, {user["name"]}!', 'success')
                
                # Redirect to admin dashboard if admin, otherwise user dashboard
                if user.get('is_admin', False):
                    return redirect(url_for('admin_dashboard'))
                
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password!', 'error')
                return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/verify-login-otp', methods=['GET', 'POST'])
def verify_login_otp():
    if 'login_otp' not in session:
        flash('Please log in first!', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        
        if otp == session.get('login_otp'):
            # OTP verified - login user
            user = session['login_user']
            session.permanent = True
            session['phone_number'] = user['phone_number']
            session['name'] = user['name']
            session['is_admin'] = user.get('is_admin', False)
            
            # Clear login session data
            session.pop('login_otp', None)
            session.pop('login_phone', None)
            session.pop('login_user', None)
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            
            # Redirect to admin dashboard if admin, otherwise user dashboard
            if user.get('is_admin', False):
                return redirect(url_for('admin_dashboard'))
            
            # Redirect to next page if exists, otherwise dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    return render_template('verify_otp.html', page_type='login')

@app.route('/dashboard')
@login_required
def dashboard():
    phone_number = session.get('phone_number')
    username = session.get('username')
    
    if phone_number:
        user = get_user_by_phone(phone_number)
    else:
        user = get_user_by_username(username)
    
    if not user:
        flash('User not found!', 'error')
        return redirect(url_for('login'))
    
    # Convert created_at string to datetime object for template
    user_data = {
        'name': user['name'],
        'phone_number': user.get('phone_number'),
        'created_at': datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
    }
    
    return render_template('dashboard.html', user=user_data)

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
    
    phone_number = session.get('phone_number')
    username = session.get('username')
    
    if phone_number:
        user = get_user_by_phone(phone_number)
    else:
        user = get_user_by_username(username)
    
    user_data = {
        'name': user['name'],
        'phone_number': user.get('phone_number')
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
    
    phone_number = session.get('phone_number')
    username = session.get('username')
    
    if phone_number:
        user = get_user_by_phone(phone_number)
    else:
        user = get_user_by_username(username)
    
    user_data = {
        'name': user['name'],
        'phone_number': user.get('phone_number')
    }
    
    return render_template('homestay_details.html', homestay=homestay, user=user_data)


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

        if not from_date or not till_date:
            flash('Please select both dates.', 'error')
            return redirect(url_for('book_homestay', homestay_id=homestay_id))

        nights = compute_nights(from_date, till_date)
        if not nights:
            flash('Till date must be after from date.', 'error')
            return redirect(url_for('book_homestay', homestay_id=homestay_id))

        price_per_night = homestay.get('price', 0) or 0
        total_amount = price_per_night * nights

        session['pending_booking'] = {
            'homestay_id': homestay_id,
            'from_date': from_date,
            'till_date': till_date,
            'nights': nights,
            'price_per_night': price_per_night,
            'total_amount': total_amount,
            'homestay_owner': homestay.get('owner'),
            'homestay_contact': homestay.get('contact'),
            'homestay_image': homestay.get('image'),
        }

        return redirect(url_for('payment'))

    return render_template('book_homestay.html', homestay=homestay)


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
        user_name = session.get('name')
        booking_payload = {
            'homestay_id': pending['homestay_id'],
            'from_date': pending['from_date'],
            'till_date': pending['till_date'],
            'nights': pending['nights'],
            'total_amount': pending['total_amount'],
            'status': 'paid',
            'payment_reference': payment_ref,
            'user_phone': session.get('phone_number'),
            'user_username': session.get('username'),
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
    user_phone = session.get('phone_number')
    username = session.get('username')
    user_name = session.get('name')

    try:
        query = supabase.table('bookings').select('*')
        if user_phone:
            query = query.eq('user_phone', user_phone)
        elif username:
            query = query.eq('user_username', username)
        response = query.order('from_date', desc=False).execute()
        bookings_data = response.data if response.data else []
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
    
    admin_name = session.get('name', 'Admin')
    return render_template('admin_dashboard.html', homestays=homestays_data, username=admin_name)

@app.route('/admin/homestay/add', methods=['GET', 'POST'])
@admin_required
def admin_add_homestay():
    """Add a new homestay"""
    if request.method == 'POST':
        try:
            features = request.form.getlist('features[]')
            if not features:
                features = [f for f in request.form.get('features', '').split(',') if f.strip()]
            
            images = [f for f in request.form.get('images', '').split(',') if f.strip()]
            if not images:
                images = [request.form.get('image', '/static/images/image.jpg')]
            
            homestay_data = {
                'owner': request.form.get('owner'),
                'rooms': int(request.form.get('rooms', 0)),
                'beds': int(request.form.get('beds', 0)),
                'floor': request.form.get('floor'),
                'rating': float(request.form.get('rating', 4.5)),
                'reviews': int(request.form.get('reviews', 0)),
                'image': request.form.get('image', '/static/images/image.jpg'),
                'images': images,
                'features': features,
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
            features = request.form.getlist('features[]')
            if not features:
                features = [f for f in request.form.get('features', '').split(',') if f.strip()]
            
            images = [f for f in request.form.get('images', '').split(',') if f.strip()]
            
            update_data = {
                'owner': request.form.get('owner'),
                'rooms': int(request.form.get('rooms', 0)),
                'beds': int(request.form.get('beds', 0)),
                'floor': request.form.get('floor'),
                'rating': float(request.form.get('rating', 4.5)),
                'reviews': int(request.form.get('reviews', 0)),
                'image': request.form.get('image'),
                'images': images,
                'features': features,
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
    session.pop('phone_number', None)
    session.pop('username', None)
    session.pop('name', None)
    session.pop('is_admin', None)
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("✅ Flask application ready!")
    print("🌐 Access at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
