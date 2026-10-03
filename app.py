import os
import re
import secrets
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

# Secret key
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "falora-dev-secret-change-me"
)

# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------
#
# LOCAL:
#   SQLite -> falora.db
#
# VERCEL:
#   If DATABASE_URL exists -> PostgreSQL / external database
#   If DATABASE_URL doesn't exist -> /tmp/falora.db
#
# IMPORTANT:
# Vercel's /var/task filesystem is read-only.
# Do NOT create app.instance_path there.
# ------------------------------------------------------------

db_url = os.getenv("DATABASE_URL", "").strip()

if db_url:
    # Render / Railway / Supabase / Neon etc.
    if db_url.startswith("postgres://"):
        db_url = db_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

elif os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
    # Temporary database for Vercel.
    #
    # WARNING:
    # /tmp is writable but NOT persistent.
    # For production, use DATABASE_URL.
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:////tmp/falora.db"
    )

else:
    # Local development
    BASE_DIR = os.path.dirname(
        os.path.abspath(__file__)
    )

    local_db_path = os.path.join(
        BASE_DIR,
        "falora.db"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///" + local_db_path
    )


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
    app.config["SESSION_COOKIE_SECURE"] = True


db = SQLAlchemy(app)


# ============================================================
# DATABASE MODELS
# ============================================================


class User(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(180),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(30),
        default="customer"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Product(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(180),
        nullable=False
    )

    slug = db.Column(
        db.String(220),
        unique=True,
        nullable=False
    )

    category = db.Column(
        db.String(80),
        nullable=False,
        index=True
    )

    price = db.Column(
        db.Float,
        nullable=False
    )

    old_price = db.Column(
        db.Float
    )

    rating = db.Column(
        db.Float,
        default=4.8
    )

    reviews = db.Column(
        db.Integer,
        default=0
    )

    badge = db.Column(
        db.String(60),
        default="NEW"
    )

    stock = db.Column(
        db.Integer,
        default=0
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    image = db.Column(
        db.Text,
        nullable=False
    )

    gallery = db.Column(
        db.Text,
        default=""
    )

    sizes = db.Column(
        db.String(255),
        default=""
    )

    colors = db.Column(
        db.String(255),
        default=""
    )

    featured = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Order(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_no = db.Column(
        db.String(40),
        unique=True,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    customer_name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(180),
        nullable=False
    )

    address = db.Column(
        db.Text,
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    postal_code = db.Column(
        db.String(30),
        nullable=False
    )

    payment = db.Column(
        db.String(50),
        nullable=False
    )

    subtotal = db.Column(
        db.Float,
        nullable=False
    )

    shipping = db.Column(
        db.Float,
        nullable=False
    )

    total = db.Column(
        db.Float,
        nullable=False
    )

    status = db.Column(
        db.String(40),
        default="Processing"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class OrderItem(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("order.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        nullable=False
    )

    name = db.Column(
        db.String(180),
        nullable=False
    )

    price = db.Column(
        db.Float,
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )


# ============================================================
# PRODUCT SEED DATA
# ============================================================


SEEDS = [
    (
        "Noir Velvet Handbag",
        "bags",
        189,
        239,
        "BEST SELLER",
        18,
        4.9,
        128,
        "Sculptural velvet statement bag with polished hardware for elevated everyday and evening edits.",
        "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=1200&q=88",
        ["Black", "Plum"],
        "XS,S,M",
        "Black,Plum",
        True,
    ),
    (
        "Aurelia Gold Watch",
        "watches",
        329,
        399,
        "LIMITED",
        9,
        4.8,
        94,
        "Minimal dial, luminous details and a refined gold-tone finish for a timeless luxury profile.",
        "https://images.unsplash.com/photo-1524805444758-089113d48a6d?auto=format&fit=crop&w=1200&q=88",
        ["Gold"],
        "One Size",
        "Gold",
        True,
    ),
    (
        "Luna Silk Heels",
        "shoes",
        159,
        199,
        "NEW DROP",
        24,
        4.7,
        76,
        "Satin-finish heels with a refined silhouette, made for statement entrances and polished nights out.",
        "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=1200&q=88",
        ["Ivory", "Plum"],
        "36,37,38,39,40",
        "Ivory,Plum",
        True,
    ),
    (
        "Obsidian Signature Shades",
        "accessories",
        119,
        149,
        "TRENDING",
        31,
        4.8,
        63,
        "Bold oversized frames with a dark editorial finish for an instantly elevated look.",
        "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=1200&q=88",
        ["Obsidian"],
        "One Size",
        "Black",
        True,
    ),
    (
        "Amethyst Glow Serum",
        "beauty",
        89,
        109,
        "GLOW PICK",
        42,
        4.9,
        211,
        "A luminous skincare essential presented in a jewel-inspired bottle for a premium night routine.",
        "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=1200&q=88",
        ["Violet"],
        "One Size",
        "Violet",
        True,
    ),
    (
        "Velour Night Fragrance",
        "beauty",
        145,
        179,
        "ICONIC",
        15,
        4.9,
        167,
        "Dark, sensual fragrance concept with an evening-ready character and premium bottle silhouette.",
        "https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=1200&q=88",
        ["Black"],
        "50ml,100ml",
        "Black",
        True,
    ),
    (
        "Eclipse Leather Sneakers",
        "shoes",
        139,
        169,
        "HOT",
        28,
        4.6,
        52,
        "Clean leather sneakers with a monochrome profile designed for luxury streetwear styling.",
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=1200&q=88",
        ["Black", "White"],
        "36,37,38,39,40,41",
        "Black,White",
        False,
    ),
    (
        "Royal Mini Tote",
        "bags",
        209,
        259,
        "EDITOR'S PICK",
        12,
        4.8,
        88,
        "Compact structured tote with polished details and a rich editorial color story.",
        "https://images.unsplash.com/photo-1566150905458-1bf1fc113f0d?auto=format&fit=crop&w=1200&q=88",
        ["Plum", "Black"],
        "Mini",
        "Plum,Black",
        True,
    ),
    (
        "Celeste Pearl Set",
        "accessories",
        129,
        159,
        "NEW",
        20,
        4.8,
        39,
        "Pearl-inspired jewelry set with luminous details for refined styling.",
        "https://images.unsplash.com/photo-1611652022419-a9419f74343d?auto=format&fit=crop&w=1200&q=88",
        ["Pearl"],
        "One Size",
        "Pearl",
        False,
    ),
    (
        "Midnight Tailored Blazer",
        "fashion",
        249,
        299,
        "FALORA EDIT",
        14,
        4.9,
        57,
        "Sharp tailoring with a dramatic midnight silhouette for polished occasions.",
        "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?auto=format&fit=crop&w=1200&q=88",
        ["Black"],
        "S,M,L,XL",
        "Black",
        True,
    ),
    (
        "Nocturne Leather Boots",
        "shoes",
        219,
        279,
        "RUNWAY",
        11,
        4.8,
        44,
        "Sleek leather boots with a sculpted profile and confident city finish.",
        "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=1200&q=88",
        ["Black"],
        "36,37,38,39,40",
        "Black",
        False,
    ),
    (
        "Violet Hour Candle",
        "home",
        69,
        89,
        "MOOD",
        35,
        4.7,
        102,
        "A moody home fragrance accent designed around violet, amber and midnight woods.",
        "https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=1200&q=88",
        ["Violet"],
        "220g",
        "Violet",
        False,
    ),
]


# ============================================================
# HELPERS
# ============================================================


def slugify(value):
    return re.sub(
        r"[^a-z0-9]+",
        "-",
        value.lower()
    ).strip("-")


def product_dict(product):
    gallery = [
        product.image
    ]

    if product.gallery:
        gallery.extend(
            [
                item
                for item in product.gallery.split("|")
                if item
            ]
        )

    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "category": product.category,
        "price": product.price,
        "old_price": product.old_price,
        "rating": product.rating,
        "reviews": product.reviews,
        "badge": product.badge,
        "stock": product.stock,
        "description": product.description,
        "image": product.image,
        "gallery": gallery,
        "sizes": [
            x for x in product.sizes.split(",")
            if x
        ],
        "colors": [
            x for x in product.colors.split(",")
            if x
        ],
        "featured": product.featured,
    }


# ============================================================
# DATABASE SEED
# ============================================================


def seed():
    # Don't duplicate products
    if Product.query.count() > 0:
        return

    for (
        name,
        category,
        price,
        old_price,
        badge,
        stock,
        rating,
        reviews,
        description,
        image,
        gallery,
        sizes,
        colors,
        featured,
    ) in SEEDS:

        product = Product(
            name=name,
            slug=slugify(name),
            category=category,
            price=price,
            old_price=old_price,
            badge=badge,
            stock=stock,
            rating=rating,
            reviews=reviews,
            description=description,
            image=image,
            gallery="|".join(gallery),
            sizes=sizes,
            colors=colors,
            featured=featured,
        )

        db.session.add(product)

    # Default admin
    admin_email = "admin@falora.test"

    if not User.query.filter_by(
        email=admin_email
    ).first():

        admin = User(
            name="Falora Admin",
            email=admin_email,
            password_hash=generate_password_hash(
                "Falora123!"
            ),
            role="admin",
        )

        db.session.add(admin)

    db.session.commit()


# ============================================================
# INITIALIZE DATABASE
# ============================================================

try:
    with app.app_context():
        db.create_all()
        seed()

except Exception as error:
    print("DATABASE INITIALIZATION ERROR:")
    print(error)


# ============================================================
# AUTH HELPERS
# ============================================================


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(
        User,
        user_id
    )


def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):

        user = current_user()

        if not user or user.role != "admin":
            return jsonify({
                "error": "Admin authentication required"
            }), 403

        return function(*args, **kwargs)

    return wrapper


@app.context_processor
def inject():
    return {
        "current_user": current_user()
    }


# ============================================================
# PAGE ROUTES
# ============================================================


@app.get("/")
def home():
    return render_template(
        "index.html"
    )


@app.get("/shop")
def shop():
    return render_template(
        "shop.html"
    )


@app.get("/product/<int:product_id>")
def product_page(product_id):

    product = db.session.get(
        Product,
        product_id
    )

    if not product:
        return render_template(
            "404.html"
        ), 404

    related = (
        Product.query
        .filter(
            Product.category == product.category,
            Product.id != product.id
        )
        .limit(4)
        .all()
    )

    return render_template(
        "product.html",
        product=product_dict(product),
        related=[
            product_dict(item)
            for item in related
        ],
    )


@app.get("/login")
def login_page():
    return render_template(
        "auth.html",
        mode="login"
    )


@app.get("/register")
def register_page():
    return render_template(
        "auth.html",
        mode="register"
    )


@app.get("/cart")
def cart_page():
    return render_template(
        "cart.html"
    )


@app.get("/checkout")
def checkout_page():
    return render_template(
        "checkout.html"
    )


@app.get("/orders")
def orders_page():
    return render_template(
        "orders.html"
    )


@app.get("/admin")
def admin_page():
    return render_template(
        "admin.html"
    )


# ============================================================
# PRODUCT API
# ============================================================


@app.get("/api/products")
def api_products():

    search = request.args.get(
        "q",
        ""
    ).strip()

    category = request.args.get(
        "category",
        "all"
    )

    sort = request.args.get(
        "sort",
        "featured"
    )

    query = Product.query

    # Search
    if search:
        query = query.filter(
            Product.name.ilike(
                f"%{search}%"
            )
        )

    # Category
    if category != "all":
        query = query.filter_by(
            category=category
        )

    # Sorting
    if sort == "price-asc":

        query = query.order_by(
            Product.price.asc()
        )

    elif sort == "price-desc":

        query = query.order_by(
            Product.price.desc()
        )

    elif sort == "rating":

        query = query.order_by(
            Product.rating.desc()
        )

    else:

        query = query.order_by(
            Product.featured.desc(),
            Product.created_at.desc()
        )

    products = query.all()

    return jsonify([
        product_dict(product)
        for product in products
    ])


@app.get("/api/products/<int:pid>")
def api_product(pid):

    product = db.session.get(
        Product,
        pid
    )

    if not product:
        return jsonify({
            "error": "Product not found"
        }), 404

    return jsonify(
        product_dict(product)
    )


# ============================================================
# ADMIN PRODUCT CREATE
# ============================================================


@app.post("/api/products")
@admin_required
def create_product():

    data = request.get_json() or {}

    required = [
        "name",
        "category",
        "price",
        "description",
        "image",
    ]

    if any(
        not data.get(field)
        for field in required
    ):
        return jsonify({
            "error": "Missing required product fields"
        }), 400

    product = Product(
        name=data["name"],
        slug=(
            slugify(data["name"])
            + "-"
            + secrets.token_hex(2)
        ),
        category=data["category"],
        price=float(data["price"]),
        old_price=float(
            data.get("old_price")
            or data["price"]
        ),
        badge=data.get(
            "badge",
            "NEW"
        ),
        stock=int(
            data.get(
                "stock",
                0
            )
        ),
        rating=float(
            data.get(
                "rating",
                5
            )
        ),
        reviews=int(
            data.get(
                "reviews",
                0
            )
        ),
        description=data["description"],
        image=data["image"],
        gallery="|".join(
            data.get(
                "gallery",
                []
            )
        ),
        sizes=",".join(
            data.get(
                "sizes",
                []
            )
        ),
        colors=",".join(
            data.get(
                "colors",
                []
            )
        ),
        featured=bool(
            data.get(
                "featured",
                False
            )
        ),
    )

    db.session.add(product)
    db.session.commit()

    return jsonify(
        product_dict(product)
    ), 201


# ============================================================
# ADMIN PRODUCT UPDATE
# ============================================================


@app.put("/api/products/<int:pid>")
@admin_required
def update_product(pid):

    product = db.session.get(
        Product,
        pid
    )

    if not product:
        return jsonify({
            "error": "Product not found"
        }), 404

    data = request.get_json() or {}

    for field in [
        "name",
        "category",
        "badge",
        "description",
        "image",
    ]:

        if field in data:
            setattr(
                product,
                field,
                data[field]
            )

    for field in [
        "price",
        "old_price",
        "rating",
    ]:

        if field in data:
            setattr(
                product,
                field,
                float(data[field])
            )

    for field in [
        "stock",
        "reviews",
    ]:

        if field in data:
            setattr(
                product,
                field,
                int(data[field])
            )

    if "sizes" in data:
        product.sizes = ",".join(
            data["sizes"]
        )

    if "colors" in data:
        product.colors = ",".join(
            data["colors"]
        )

    if "gallery" in data:
        product.gallery = "|".join(
            data["gallery"]
        )

    if "featured" in data:
        product.featured = bool(
            data["featured"]
        )

    db.session.commit()

    return jsonify(
        product_dict(product)
    )


# ============================================================
# ADMIN PRODUCT DELETE
# ============================================================


@app.delete("/api/products/<int:pid>")
@admin_required
def delete_product(pid):

    product = db.session.get(
        Product,
        pid
    )

    if not product:
        return jsonify({
            "error": "Product not found"
        }), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({
        "ok": True
    })


# ============================================================
# AUTH REGISTER
# ============================================================


@app.post("/api/auth/register")
def api_register():

    data = request.get_json() or {}

    name = data.get(
        "name",
        ""
    ).strip()

    email = data.get(
        "email",
        ""
    ).strip().lower()

    password = data.get(
        "password",
        ""
    )

    if (
        not name
        or not email
        or len(password) < 6
    ):
        return jsonify({
            "error": (
                "Name, valid email and "
                "password 6+ characters "
                "are required"
            )
        }), 400

    existing_user = User.query.filter_by(
        email=email
    ).first()

    if existing_user:
        return jsonify({
            "error": "Email already registered"
        }), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(
            password
        ),
    )

    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id

    return jsonify({
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    }), 201


# ============================================================
# AUTH LOGIN
# ============================================================


@app.post("/api/auth/login")
def api_login():

    data = request.get_json() or {}

    email = data.get(
        "email",
        ""
    ).strip().lower()

    password = data.get(
        "password",
        ""
    )

    user = User.query.filter_by(
        email=email
    ).first()

    if (
        not user
        or not check_password_hash(
            user.password_hash,
            password
        )
    ):
        return jsonify({
            "error": "Email or password is incorrect"
        }), 401

    session["user_id"] = user.id

    return jsonify({
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    })


# ============================================================
# AUTH LOGOUT
# ============================================================


@app.post("/api/auth/logout")
def api_logout():

    session.clear()

    return jsonify({
        "ok": True
    })


# ============================================================
# AUTH CURRENT USER
# ============================================================


@app.get("/api/auth/me")
def api_me():

    user = current_user()

    return jsonify({
        "user": (
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            }
            if user
            else None
        )
    })


# ============================================================
# CREATE ORDER
# ============================================================


@app.post("/api/orders")
def create_order():

    data = request.get_json() or {}

    items = data.get(
        "items",
        []
    )

    if not items:
        return jsonify({
            "error": "Cart is empty"
        }), 400

    subtotal = 0
    prepared = []

    for item in items:

        try:
            product_id = int(
                item.get("id")
            )

            quantity = max(
                1,
                int(
                    item.get(
                        "quantity",
                        1
                    )
                )
            )

        except (
            TypeError,
            ValueError
        ):
            return jsonify({
                "error": "Invalid cart item"
            }), 400

        product = db.session.get(
            Product,
            product_id
        )

        if (
            not product
            or product.stock < quantity
        ):
            return jsonify({
                "error": (
                    f"Product unavailable: "
                    f"{product_id}"
                )
            }), 400

        subtotal += (
            product.price
            * quantity
        )

        prepared.append(
            (
                product,
                quantity
            )
        )

    shipping = (
        0
        if subtotal >= 150
        else 12
    )

    total = (
        subtotal
        + shipping
    )

    logged_user = current_user()

    customer_name = (
        data.get("customer_name")
        or (
            logged_user.name
            if logged_user
            else "Guest Customer"
        )
    )

    email = (
        data.get("email")
        or (
            logged_user.email
            if logged_user
            else ""
        )
    )

    if (
        not email
        or not data.get("address")
        or not data.get("city")
        or not data.get("postal_code")
    ):
        return jsonify({
            "error": (
                "Complete customer "
                "and shipping details"
            )
        }), 400

    order = Order(
        order_no=(
            "FLR-"
            + datetime.utcnow().strftime(
                "%y%m%d"
            )
            + "-"
            + secrets.token_hex(
                3
            ).upper()
        ),
        user_id=(
            logged_user.id
            if logged_user
            else None
        ),
        customer_name=customer_name,
        email=email,
        address=data["address"],
        city=data["city"],
        postal_code=data["postal_code"],
        payment=data.get(
            "payment",
            "Card"
        ),
        subtotal=subtotal,
        shipping=shipping,
        total=total,
    )

    try:

        db.session.add(order)

        db.session.flush()

        for product, quantity in prepared:

            product.stock -= quantity

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                name=product.name,
                price=product.price,
                quantity=quantity,
            )

            db.session.add(
                order_item
            )

        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify({
            "error": "Could not create order"
        }), 500

    return jsonify({
        "order_no": order.order_no,
        "total": order.total,
        "status": order.status,
    }), 201


# ============================================================
# GET ORDERS
# ============================================================


@app.get("/api/orders")
def get_orders():

    user = current_user()

    if not user:
        return jsonify({
            "error": "Login required"
        }), 401

    orders = (
        Order.query
        .filter_by(
            user_id=user.id
        )
        .order_by(
            Order.created_at.desc()
        )
        .all()
    )

    return jsonify([
        {
            "order_no": order.order_no,
            "total": order.total,
            "status": order.status,
            "created_at": (
                order.created_at.isoformat()
            ),
            "payment": order.payment,
        }
        for order in orders
    ])


# ============================================================
# 404 HANDLER
# ============================================================


@app.errorhandler(404)
def not_found(error):

    if request.path.startswith("/api/"):

        return jsonify({
            "error": "Not found"
        }), 404

    return render_template(
        "404.html"
    ), 404


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                5000
            )
        ),
        debug=True,
    )