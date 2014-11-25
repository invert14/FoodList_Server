import json
from json.decoder import JSONDecoder
from flask import Flask, request
from pony.orm import *

app = Flask(__name__)
db = Database("sqlite", "stockmanager.sqlite", create_db=True)


class Product(db.Entity):
    # id = PrimaryKey(int, auto=True)
    name = PrimaryKey(str)
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


def updateProductAmount(deviceId, newAmount, product):
    oldProductAmount = get(pa for pa in ProductAmount if pa.product == product and pa.device == deviceId)
    print oldProductAmount
    if oldProductAmount is not None:
        oldProductAmount.amount = newAmount
    else:
        newProductAmount = ProductAmount(product=product, device=deviceId, amount=newAmount)

@app.route('/product', methods=['GET'])
def get_product():
    if request.method == 'GET':
        print 'GET!!!!!!'
        name = request.args.get('name', '')
        with db_session:
            product = get(p for p in Product if p.name == name)
            if product is None:
                product = Product(name = name, amount = 0, user = 1)
    response = [dict(name=product.name, amount=product.amount)]
    return json.dumps(response)

@app.route('/products', methods=['GET', 'POST'])
def sync():
    products = []
    productsToBeDeleted = []
    userId = 1
    if request.method == 'GET':
        userId = request.args.get('user_id', '')
    else:
        userId = int(request.form['user_id'])
        deviceId = int(request.form['device_id'])
        productsJson = request.form['products']
        products = JSONDecoder().decode(productsJson)
        productsToBeDeleted = JSONDecoder().decode(request.form['productsToBeDeleted'])
        print productsToBeDeleted

        print userId
        print deviceId

    with db_session:
        user = get(u for u in User if u.id == userId)

        for p in products:
            productList = json.loads(p)
            productParams = dict(productList)
            for key, value in productParams.items():
                print key, value
            productName = productParams["name"]
            newAmount = productParams["localAmount"]

            product = get(p for p in Product if p.name == productName)
            if product is not None:
                print 'found product'
            else:
                print 'NEW PRODUCT'
                product = Product(name=productName, amount=newAmount, user=user)
                commit()
            print product.productAmounts
            updateProductAmount(deviceId, newAmount, product)

        for p in productsToBeDeleted:
            productName = p[1:-1]
            product = get(p for p in Product if p.name == productName)
            for pa in product.productAmounts:
                pa.delete()
            product.delete()

    with db_session:
        user_products = select(p for p in Product if p.user.id == userId)[:]
        print user_products
        for p in user_products:
            amounts = select([pa.amount] for pa in ProductAmount if pa.product == p).without_distinct()
            p.amount = sum(amounts)

    response = []
    with db_session:
        user_products = select(p for p in Product if p.user.id == userId)[:]
        for p in user_products:
            response.append(dict(name=p.name, amount=p.amount))
    return json.dumps(response)

if __name__ == '__main__':
    db.generate_mapping(check_tables=True, create_tables=True)
    app.debug = True
    sql_debug(True)
    app.run(host='0.0.0.0')