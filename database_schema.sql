-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Create index for faster username lookups
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create homestays table
CREATE TABLE IF NOT EXISTS homestays (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    rooms INTEGER NOT NULL,
    beds INTEGER NOT NULL,
    floor INTEGER,
    rating DECIMAL(2,1),
    reviews INTEGER DEFAULT 0,
    image TEXT,
    images TEXT[],
    features TEXT[],
    description TEXT,
    price INTEGER,
    contact TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Insert admin user (username: admin, password: admin123)
INSERT INTO users (username, email, password_hash, is_admin) VALUES
('admin', 'admin@kangundi.com', 'scrypt:32768:8:1$Bkj2Mqqe5Y8OI7b3$e8a4431376cac0510679b71685a38652d8d3cc4a145db4e6df4ac51123805be5315f9efeba3e2b7a40a41031a0871142f3355e897e13e8acc49bcca45c792ba3', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Insert sample homestay data
INSERT INTO homestays (name, owner, rooms, beds, floor, rating, reviews, image, images, features, description, price, contact) VALUES
('Cozy Mountain View', 'Rajesh Kumar', 3, 6, 1, 4.8, 124, '/static/images/image.jpg', 
 ARRAY['/static/images/image.jpg', '/static/images/logo.jpg', '/static/images/image.jpg', '/static/images/logo.jpg'],
 ARRAY['Geyser', 'AC', 'WiFi', 'Kitchen'],
 'A beautiful homestay with stunning mountain views, perfect for climbers visiting Kangundi. Close to all major climbing areas.', 
 1500, '+91-9876543210'),

('Climbers Paradise', 'Meera Patel', 2, 4, 2, 4.9, 89, '/static/images/logo.jpg',
 ARRAY['/static/images/logo.jpg', '/static/images/image.jpg', '/static/images/logo.jpg'],
 ARRAY['Geyser', 'WiFi', 'Parking'],
 'Popular among climbers, with gear storage and local beta. Walking distance to main bouldering zones.', 
 1200, '+91-9876543211'),

('Rock Base Camp', 'Amit Singh', 4, 8, 1, 4.7, 156, '/static/images/image.jpg',
 ARRAY['/static/images/image.jpg', '/static/images/logo.jpg', '/static/images/image.jpg', '/static/images/logo.jpg'],
 ARRAY['Geyser', 'AC', 'WiFi', 'Kitchen', 'Parking'],
 'Large homestay perfect for groups. Spacious rooms and common areas. Host is an experienced climber.', 
 2000, '+91-9876543212'),

('Valley View Retreat', 'Priya Sharma', 2, 4, 3, 4.6, 78, '/static/images/logo.jpg',
 ARRAY['/static/images/logo.jpg', '/static/images/image.jpg', '/static/images/logo.jpg'],
 ARRAY['Geyser', 'WiFi'],
 'Quiet homestay with beautiful valley views. Great for rest days between climbing sessions.', 
 1000, '+91-9876543213'),

('Sandstone Haven', 'Vikram Reddy', 3, 6, 2, 4.8, 112, '/static/images/image.jpg',
 ARRAY['/static/images/image.jpg', '/static/images/logo.jpg', '/static/images/image.jpg', '/static/images/logo.jpg'],
 ARRAY['Geyser', 'AC', 'WiFi', 'Kitchen'],
 'Modern homestay with all amenities. Perfect location for exploring Kangundi bouldering areas.', 
 1600, '+91-9876543214'),

('Boulder Lodge', 'Anita Verma', 2, 5, 1, 4.9, 134, '/static/images/logo.jpg',
 ARRAY['/static/images/logo.jpg', '/static/images/image.jpg', '/static/images/logo.jpg', '/static/images/image.jpg'],
 ARRAY['Geyser', 'WiFi', 'Parking', 'Kitchen'],
 'Cozy lodge run by climbing enthusiasts. Great community vibe and local knowledge.', 
 1300, '+91-9876543215');
