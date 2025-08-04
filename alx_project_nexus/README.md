# MART AFRICA
- **Overview**
This is my final project

- **Setup Django**
```bash
python -m venv venv  # create a virtuel environment
pip install -r requirements.txt  # install all requirements need for this project
# these are the commands i used to setup the project
django-admin startproject mart_africa
python manage.py startapp users  # for my user auth and management
python manage.py startapp products  # for products management
python manage.py startapp orders # for order management
python manage.py startapp reviews
# Test Db
python manage.py dbshell
python manage.py collectstatic
```

#### Project Structure 
- **mart_africa/**
- ├── requirements.txt
- ├── .env
- |-- README.md
- ├── mart_africa/
- │   ├── settings.py
- │   └── urls.py
- └── apps/
-    ├── accounts/     # User authentication
-   ├── products/     # Product management
-    ├── orders/       # Order processing
-   └── categories/     # Category handling

- Install drf-yasg for Swagger documentation.
Configure Swagger to automatically document all APIs. The documentation should be available at /swagger/.

#### Users App Features

###### 1. Models Created

- User Model extending Django's AbstractUser
- ShippingAddress Model with one-to-one relationship
- Automatic has_shipping_address flag update
- Clean database relationships
###### 2. Virtual Properties

- User registration with password validation
- JWT login/logout with custom claims
- Token refresh functionality
- Password change endpoint
- Secure authentication using Django's built-in features
###### 3. API Endpoints
``` http
- **Public Endpoints**
POST /api/register/          # User registration
POST /api/login/             # User login
POST /api/refresh/     # Refresh JWT token
```
- **👤 Regular User Endpoints:**
```http
GET  /api/dashboard/         # User personal dashboard
POST /api/logout/            # User logout
GET/PATCH /api/profile/      # User profile management
POST /api/change-password/   # Change password
GET/POST/PATCH /api/shipping-address/  # Shipping address CRUD
```
- **🛡️ Admin-Only Endpoints:**
```http
GET  /api/admin/dashboard/           # Admin system dashboard
GET  /api/admin/users/               # List all users
GET/PATCH/DELETE  /api/admin/users/{id}/          # Get user details CRUD
```

###### 4. Role-Based Features:
- **📊 Admin Dashboard:**

- Total users count
- Admin vs regular users statistics
- Users with shipping addresses
- Recent user registrations
- Full system overview

- **👤 Regular User Dashboard:**

- Personal profile information
- Profile completion status
- Personal statistics (orders, wishlist - ready for expansion)
- User-specific data only

#### 🛍️ Products App Features

###### 1. Models Created

- **Product** – Main product model with all virtual properties  
- **Category** – Product categories  
- **ProductImage** – Multiple images per product using Cloudinary    
- **Wishlist** – User wishlist functionality  

###### 2. Virtual Properties

- ✅ `qty_left` – `total_qty - total_sold`  
- ✅ `total_reviews` – Count of reviews  
- ✅ `average_rating` – Average rating from reviews  
- ✅ `is_in_stock` – Stock availability check  
- ✅ `is_low_stock` – Low stock warning  

###### 3. Image Upload Features

- Cloudinary integration with automatic transformations  
- Multiple images per product with primary image designation  
- Image compression and format optimization  
- Alt text for accessibility  

###### 4. API Endpoints

##### 📦 Products
```http
GET    /api/products/                     # List products (with filters)
POST   /api/products/                     # Create product (Admin)
GET    /api/products/{id}/                # Get product details
PATCH  /api/products/{id}/                # Update product (Owner/Admin)
DELETE /api/products/{id}/                # Delete product (Owner/Admin)
POST   /api/products/{id}/images/         # Upload additional images
```

##### Catregories
```http
GET    /api/products/categories/          # List categories
POST   /api/products/categories/          # Create category (Admin)
GET    /api/products/categories/{id}/     # Get category details
```
##### ❤️ Wishlist
```http
GET    /api/products/wishlist/            # Get user wishlist
POST   /api/products/wishlist/            # Add to wishlist
DELETE /api/products/wishlist/{id}/       # Remove from wishlist
```

##### 🛡️ Admin Endpoints
```http
GET    /api/products/admin/stats/         # Product statistics
GET    /api/products/admin/low-stock/     # Low stock products
```
#### Reviews App Features

###### 1. Models
- **Review** – Product reviews with ratings

###### 2. API Endpoints
```http
GET   /api/{id}/reviews
POST  /product/{id}/reviews
```

#### SWAGGER DOCUMENTAION
```http
GET /swagger       # web UI 
GET /swagger-docs  # to download the documentation 
```
on my live hosting
```http
https://martafrica.onrender.com/swagger/
https://martafrica.onrender.com/swagger-docs/
```
