import json
from json.decoder import JSONDecoder
from flask import Flask, request
from pony.orm import *

app = Flask(__name__)
db = Database("sqlite", "stockmanager.sqlite", create_db=True)


class Product(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    amount = Required(int)
    user = Required("User")
    productAmounts = Set("ProductAmount")


class ProductAmount(db.Entity):
    id = PrimaryKey(int, auto=True)
    product = Required("Product")
    device = Required(int)
    amount = Required(int)


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
def sync():
    products = []
    userId = 1
    if request.method == 'GET':
        userId = request.args.get('user_id', '')
    else:
        userId = int(request.form['user_id'])
        deviceId = int(request.form['device_id'])
        productsJson = request.form['products']
        products = JSONDecoder().decode(productsJson)
        # print products
        print userId
        print deviceId

    with db_session:
        user = get(u for u in User if u.id == userId)
        for p in products:
            productList = json.loads(p)
            productParams = dict(productList)
            for key, value in productParams.items():
                print key, value
            productId = productParams["id"]
            newAmount = productParams["localAmount"]
            if productId == 0:
                print 'NEW PRODUCT'
                product = Product(name=productParams["name"],amount=newAmount,user=user)
            else:
                print 'found product'
                product = get(p for p in Product if p.id == productId)
            print product
            oldProductAmount = get(pa for pa in ProductAmount if pa.product == product and pa.device == deviceId)
            print oldProductAmount
            if oldProductAmount is not None:
                oldProductAmount.amount = newAmount
            else:
                newProductAmount = ProductAmount(product=product, device=deviceId, amount=newAmount)

    with db_session:
        user_products = select(p for p in Product if p.user.id == userId)[:]
        print user_products
        for p in user_products:
            amounts = select([pa.amount] for pa in ProductAmount if pa.product == p)[:]
            p.amount = sum(amounts)

    response = []
    with db_session:
        user_products = select(p for p in Product if p.user.id == userId)[:]
        for p in user_products:
            response.append(dict(id=p.id, name=p.name, amount=p.amount))
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
    db.generate_mapping(check_tables=True, create_tables=True)
    app.debug = True
    sql_debug(True)
    app.run(host='0.0.0.0')