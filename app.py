from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Table, Column, String, select, Float, DateTime
from marshmallow import ValidationError
from typing import List, Optional


#initializing the Flask app
app = Flask(__name__)

#Connecting to the MYSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:KenAstro!@localhost/ecommerce_api'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#creating our Base Model
class Base(DeclarativeBase): #this is the base model for all our models
    pass

def generate_uuid(): #this function generates a unique id for our models
    return str(uuid.uuid4())

#initializing SQLAlchemy and Marshmallow
db = SQLAlchemy(model_class=Base)
db.init_app(app)
ma = Marshmallow(app)

#Creating a many-to-many Association table between Orders and Products
orders_products = Table(
    "orders_products",
    Base.metadata,
    Column("order_id", ForeignKey("orders.id"), primary_key=True),
    Column("product_id", ForeignKey("products.id"), primary_key=True)
)

#==============Models===============#

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable = False)
    address: Mapped[str] = mapped_column(String(150), nullable = False)
    email: Mapped[str] = mapped_column(String(50), nullable = False)

    # One-to-Many relationship showing one user can have many orders
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(60), nullable = False)
    price: Mapped[float] = mapped_column(Float(8), nullable = False)

    # Many to Many relationship showing many products can be in many orders
    orders: Mapped[List["Order"]] = relationship(secondary="orders_products", back_populates="products")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key = True, autoincrement=True)
    order_date: Mapped[DateTime] = mapped_column(DateTime, nullable = False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable = False)

    # One-to-Many relationship showing one user can have many orders
    user: Mapped["User"] = relationship("User", back_populates="orders") 

    # Many to Many relationship showing many orders can have many products
    products: Mapped[List["Product"]] = relationship(secondary="orders_products", back_populates="orders")

#==============Marshmallow Schemas===============#
#User Schema   
class UserSchema(ma.SQLAlchemyAutoSchema): #the 'ma' is inheriting from the Marshmallow instance on line 27
    class Meta:
        model = User

#Product Schema
class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product

#Order Schema
class OrderSchema(ma.SQLAlchemyAutoSchema): 
    class Meta:
        model = Order

#Initializing the Schemas
user_schema = UserSchema()
users_schema = UserSchema(many=True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

#=================================Routes===================================#

#---------------USER Endpoints-----------------#
#CREATE a new user
@app.route('/users', methods=['POST'])
def create_user():
    try:
        user_data = user_schema.load(request.json) #this will load the incoming JSON data into a User object
    except ValidationError as err:
        return jsonify(err.messages), 400 #returns a 400 error code if unable to load the data
    
    exists = db.session.query(User).filter_by(email=user_data['email']).first() #checks if the user already exists
    if exists:
        return jsonify({"message": f"User with email {user_data['email']} already exists"}), 400 #returns a 400 error code if the user already exists
    else:
        new_user = User(name = user_data['name'], address = user_data['address'], email = user_data['email'])
        db.session.add(new_user)
        db.session.commit()
        print(f"User {new_user.name} created")

    return user_schema.jsonify(new_user), 201 #returns the new user as a JSON object with a 201 status code

#GET ALL users
@app.route('/users', methods = ['GET'])
def get_users():
    query = select(User)
    users = db.session.execute(query).scalars().all() #scalars returns the results in a list form and all() returns all the individuals results
    return users_schema.jsonify(users), 200 #returns the users as a JSON object with a 200 status code

#GET a single user
@app.route('/user/<int:id>', methods = ['GET'])
def get_user(id):
    user = db.session.get(User, id) #scalar returns the results in a single form
    return user_schema.jsonify(user), 200

#UPDATE a user
@app.route('/users/<int:id>', methods = ['PUT'])
def update_user(id):
    user = db.session.get(User, id)
    if not user:
        return jsonify({"message": "Invalid user id"})
    try:
        user_data = user_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    user.name = user_data['name']
    user.address = user_data['address']
    user.email = user_data['email']
    db.session.commit()
    return user_schema.jsonify(user), 200

#Delete User
@app.route('/user/<int:id>', methods = ['DELETE'])
def delete_user(id):
    user = db.session.get(User, id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"user with id {id} deleted"}), 200
    else:
        return jsonify({"message": f"user with {id} not found"}), 400
    
#---------------PRODUCT Endpoints-----------------#
#CREATE a new user
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json) 
    except ValidationError as err:
        return jsonify(err.messages), 400 
    
    exists = db.session.query(Product).filter_by(product_name=product_data['product_name']).first() 
    if exists:
        return jsonify({"message": f"Product with name {product_data['product_name']} already exists"}), 400 
    else:
        new_product = Product(product_name = product_data['product_name'], price = product_data['price'])
        db.session.add(new_product)
        db.session.commit()
        print(f"Product {new_product.product_name} created")

    return product_schema.jsonify(new_product), 201 

@app.route('/products', methods = ['GET'])
def get_products():
    query = select(Product)
    products = db.session.execute(query).scalars().all()
    return products_schema.jsonify(products), 200 

#GET a single product
@app.route('/product/<int:id>', methods = ['GET'])
def get_product(id):
    product = db.session.get(Product, id)
    return product_schema.jsonify(product), 200

#UPDATE a product
@app.route('/product/<int:id>', methods = ['PUT'])
def update_product(id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"message": "Invalid product id"})
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    product.product_name = product_data['product_name']
    product.price = product_data['price']
    db.session.commit()
    return product_schema.jsonify(product), 200

# #Delete User
# @app.route('/user/<int:id>', methods = ['DELETE'])
# def delete_user(id):
#     user = db.session.get(User, id)
#     if user:
#         db.session.delete(user)
#         db.session.commit()
#         return jsonify({"message": f"user with id {id} deleted"}), 200
#     else:
#         return jsonify({"message": f"user with {id} not found"}), 400

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    app.run(debug=True)

