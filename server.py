import json
from flask import Flask, request
from pony.orm import *
from pprint import pprint

app = Flask(__name__)
db = Database("sqlite", "stockmanager.sqlite", create_db=True)


class Product(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    amount = Required(int)
    user = Required("User")


class User(db.Entity):
    id = PrimaryKey(int, auto=True)
    login = Required(str, unique=True)
    password = Required(str)
    products = Set(Product)


@app.route('/user', methods=['GET', 'POST'])
def user():
    if request.method == 'GET':
        print 'GET!!!!!!'
        user_login = request.args.get('login', '')
        user_password = request.args.get('password', '')
    else:
        print 'POST!!!!!!'
        user_login = request.form['login']
        user_password = request.form['password']
    print 'siema'
    print 'login: ' + user_login
    print 'password: ' + user_password
    with db_session:
        user = get(u for u in User if u.login == user_login and u.password == user_password)
    print user.id
    return str(user.id)


@app.route('/products', methods=['GET', 'POST'])
def products():
    user_id = 1
    if request.method == 'GET':
        user_id = request.args.get('user_id', '')
    else:
        user_id = request.form['user_id']
    with db_session:
        user_products = select([p.id, p.name, p.amount] for p in Product if p.user.id == user_id)[:]
    response = []
    for p in user_products:
        response.append(dict(id=p[0], name=p[1], amount=p[2]))
    return json.dumps(response)


@app.route('/take', methods=['GET', 'POST'])
def take():
    product_id = request.args.get('product_id', '')
    amount = request.args.get('amount', '')
    with db_session:
        product = Product.get(id=product_id)
        product.amount -= int(amount)
    return product.id


@app.route('/add', methods=['GET', 'POST'])
def add():
    product_id = request.args.get('product_id', '')
    amount = request.args.get('amount', '')
    with db_session:
        product = Product.get(id=product_id)
        product.amount += int(amount)
    return str(product.id)


@app.route('/new', methods=['GET', 'POST'])
def new():
    product_name = request.args.get('product_name', '')
    user_id = request.args.get('user_id', '')
    with db_session:
        user = get(u for u in User if u.id == user_id)
        product = Product(name=product_name, amount=0, user=user)
        commit()
    return "OK"


@app.route('/delete', methods=['GET', 'POST'])
def delete():
    product_id = request.args.get('product_id', '')
    with db_session:
        Product[product_id].delete()
    return "OK"


if __name__ == '__main__':
    db.generate_mapping(create_tables=True)
    app.debug = True
    sql_debug(True)
    app.run(host='0.0.0.0')