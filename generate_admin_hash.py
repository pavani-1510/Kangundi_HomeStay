#!/usr/bin/env python3
"""
Generate password hash for admin user.
Run this to get the hash for the admin password 'admin123'
"""
from werkzeug.security import generate_password_hash

password = 'admin123'
hash_value = generate_password_hash(password)

print("Admin Password Hash:")
print(hash_value)
print("\nUse this in your SQL INSERT statement:")
print(f"INSERT INTO users (username, email, password_hash, is_admin) VALUES")
print(f"('admin', 'admin@kangundi.com', '{hash_value}', TRUE);")
