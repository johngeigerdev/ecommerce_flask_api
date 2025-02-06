from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Table, Column, String, select, Float
from marshmallow import ValidationError, Schema, fields
from typing import List, Optional
import uuid
from datetime import datetime
import pytz


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
    order_date: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.now(pytz.timezone("US/Eastern")), nullable=False)
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
    user_id = fields.Int(required=True)
    order_date = fields.DateTime(dump_only=True) #dump_only means that the field is not required to be inputted but will be displayed in the output

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
#CREATE a new product
@app.route('/products', methods=['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json) #this loads the incoming JSON data into a Product object
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

#GET products
@app.route('/products', methods = ['GET'])
def get_products():
    query = select(Product)
    products = db.session.execute(query).scalars().all() #with the variable product, this will return all the products in the database
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

#Delete Product
@app.route('/product/<int:id>', methods = ['DELETE'])
def delete_product(id):
    product = db.session.get(Product, id) 
    if product:
        db.session.delete(product)
        db.session.commit()
        return jsonify({"message": f"product with id {id} deleted"}), 200
    else:
        return jsonify({"message": f"product with {id} not found"}), 400

#---------------ORDER Endpoints-----------------#
#CREATE a new order
@app.route('/order', methods=['POST'])
def create_order():
    try:
        order_data = order_schema.load(request.json) 
    except ValidationError as err:
        return jsonify(err.messages), 400

    order_data = request.json
    new_order = Order(user_id = order_data.get('user_id'))
    db.session.add(new_order)
    db.session.commit()
    return jsonify({
        "message": f"Order created successfully",
        "order_id": new_order.id,
        "order_date": new_order.order_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(new_order.order_date, datetime) else new_order.order_date
    })

#GET orders
@app.route('/orders', methods = ['GET'])
def get_orders():
    orders = db.session.query(Order).all()
    orders_list = []
    for order in orders:
        orders_list.append({
            'id': order.id,
            'order_date': order.order_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(order.order_date, datetime) else order.order_date
        })
    return jsonify(orders_list)

# #GET a single order
@app.route('/product/<int:id>', methods = ['GET'])
def get_order(id):
    order = db.session.get(Order, id)
    return order_schema.jsonify(order), 200

#ADD a product to an order (PUT)
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods = ['PUT'])
def add_product_to_order(order_id, product_id):
    order = db.session.get(Order, order_id) 
    product = db.session.get(Product, product_id)
    if not order:
        return jsonify({"message": "Invalid order id"}), 400
    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    if product in order.products: #ensures that there are no duplicate items in the order
        return jsonify({"message": f"{product.product_name} is already in the order"}), 400
    else:
        order.products.append(product)
        db.session.commit()
    return jsonify({"message": f"Product {product.product_name} added to order {order.id}"}), 200

#remove product from an order
@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods = ['PUT'])
def remove_product(order_id, product_id):
    order = db.session.get(Order, order_id)
    product = db.session.get(Product, product_id)
    if not order:
        return jsonify({"message": "invalid product id"})
    if not product:
        return jsonify({"message": "invalid product id"})
    order.products.remove(product)
    db.session.commit()
    return jsonify({"message": f"{product.product_name} has been removed from order {order.id}"}), 200

#get orders for a specified user
@app.route('/orders/user/<user_id>', methods = ['GET'])
def getuserOrders(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify ({"message": "invalid user id"})
    else:
        orders = db.session.query(Order).filter_by(user_id = user.id).all() #this queries the Order table for all orders with the specified user_id
        orders_list = []
        for order in orders: #this loops through each order in the orders table that matches ther given user_id and appends to orders_list[]
            orders_list.append({
                "id": order.id,
                "order_date": order.order_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(order.order_date, datetime) else order.order_date                                   
            })
        return jsonify({"orders": orders_list}), 200
    
#get all products in an order
@app.route('/orders/<int:order_id>/products')
def get_order_products(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"message": "invalid order id"})
    else:
        products_list = []
        for product in order.products: #order.products is a list of products in the order, this is specified in the many-to-many relationship in the Order model 
            products_list.append({
                "name": product.product_name, #product_name is a column in the Product model
                "id": product.id #id is a column in the Product model
            })
        return jsonify({"products:": products_list}), 200


#UPDATE a order
@app.route('/order/<int:id>', methods = ['PUT'])
def update_order(id):
    order = db.session.get(Order, id)
    if not order:
        return jsonify({"message": "Invalid order id"})
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    order.product_name = order_data['order_name']
    order.price = order_data['price']
    db.session.commit()
    return order_schema.jsonify(order), 200

# #Delete Order
# @app.route('/order/<int:id>', methods = ['DELETE'])
# def delete_order(id):
#     order = db.session.get(Order, id)
#     if order:
#         db.session.delete(order)
#         db.session.commit()
#         return jsonify({"message": f"order with id {id} deleted"}), 200
#     else:
#         return jsonify({"message": f"order with {id} not found"}), 400





if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    app.run(debug=True)

