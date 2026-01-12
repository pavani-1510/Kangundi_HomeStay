from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Initialize Supabase client
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

supabase: Client = create_client(supabase_url, supabase_key)

# Helper functions for database operations
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

def get_user_by_email(email):
    """Get user by email"""
    try:
        response = supabase.table('users').select('*').eq('email', email).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

def create_user(username, email, password_hash, is_admin=False):
    """Create a new user in database"""
    try:
        response = supabase.table('users').insert({
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'is_admin': is_admin
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def login_required(f):
    """Decorator to protect routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to protect admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        user = get_user_by_username(session.get('username'))
        if not user or not user.get('is_admin', False):
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required!', 'error')
            return redirect(url_for('signup'))
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return redirect(url_for('signup'))
        
        # Check if user already exists
        if get_user_by_username(username):
            flash('Username already exists!', 'error')
            return redirect(url_for('signup'))
        
        if get_user_by_email(email):
            flash('Email already registered!', 'error')
            return redirect(url_for('signup'))
        
        # Create new user
        password_hash = generate_password_hash(password)
        user = create_user(username, email, password_hash)
        
        if user:
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Please enter both username and password!', 'error')
            return redirect(url_for('login'))
        
        user = get_user_by_username(username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['username'] = username
            session['is_admin'] = user.get('is_admin', False)
            if remember:
                session.permanent = True
            flash(f'Welcome back, {username}!', 'success')
            
            # Redirect to admin dashboard if admin, otherwise user dashboard
            if user.get('is_admin', False):
                return redirect(url_for('admin_dashboard'))
            
            # Redirect to next page if exists, otherwise dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    username = session.get('username')
    user = get_user_by_username(username)
    
    if not user:
        flash('User not found!', 'error')
        return redirect(url_for('login'))
    
    # Convert created_at string to datetime object for template
    user_data = {
        'username': username,
        'email': user['email'],
        'created_at': datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
    }
    
    return render_template('dashboard.html', user=user_data)

@app.route('/rooms')
@login_required
def rooms():
    """Display all available homestays"""
    try:
        # Fetch all homestays from database
        response = supabase.table('homestays').select('*').execute()
        homestays_data = response.data if response.data else []
    except Exception as e:
        print(f"Error fetching homestays: {e}")
        flash('Error loading homestays. Please try again.', 'error')
        homestays_data = []
    
    username = session.get('username')
    user = get_user_by_username(username)
    
    user_data = {
        'username': username,
        'email': user['email']
    }
    
    return render_template('rooms.html', homestays=homestays_data, user=user_data)

@app.route('/homestay/<int:homestay_id>')
@login_required
def homestay_details(homestay_id):
    """Display details of a specific homestay"""
    try:
        # Fetch specific homestay from database
        response = supabase.table('homestays').select('*').eq('id', homestay_id).execute()
        
        if not response.data or len(response.data) == 0:
            flash('Homestay not found!', 'error')
            return redirect(url_for('rooms'))
        
        homestay = response.data[0]
    except Exception as e:
        print(f"Error fetching homestay: {e}")
        flash('Error loading homestay details. Please try again.', 'error')
        return redirect(url_for('rooms'))
    
    username = session.get('username')
    user = get_user_by_username(username)
    
    user_data = {
        'username': username,
        'email': user['email']
    }
    
    return render_template('homestay_details.html', homestay=homestay, user=user_data)

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
    
    username = session.get('username')
    return render_template('admin_dashboard.html', homestays=homestays_data, username=username)

@app.route('/admin/homestay/add', methods=['GET', 'POST'])
@admin_required
def admin_add_homestay():
    """Add a new homestay"""
    if request.method == 'POST':
        try:
            # Parse features as array
            features = request.form.getlist('features[]')
            if not features:
                features = [f for f in request.form.get('features', '').split(',') if f.strip()]
            
            images = [f for f in request.form.get('images', '').split(',') if f.strip()]
            if not images:
                images = [request.form.get('image', '/static/images/image.jpg')]
            
            homestay_data = {
                'name': request.form.get('name'),
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
    
    return render_template('admin_add_homestay.html', username=session.get('username'))

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
                'name': request.form.get('name'),
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
    
    return render_template('admin_edit_homestay.html', homestay=homestay, username=session.get('username'))

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
    session.pop('username', None)
    session.pop('is_admin', None)
    flash('You have been logged out successfully!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("✅ Flask application ready!")
    print("🌐 Access at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
