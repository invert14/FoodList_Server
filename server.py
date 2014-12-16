import json
from json.decoder import JSONDecoder
from flask import Flask, request
from pony.orm import *

app = Flask(__name__)
db = Database("sqlite", "stockmanager.sqlite", create_db=True)
DEFAULT_LIST_NAME = "Default list"
DEFAULT_SHOP_NAME = "Default shop"


class Product(db.Entity):
    name = PrimaryKey(str)
    amount = Required(int)
    price = Required(float)
    shop = Required(str)
    list = Required("List")
    productAmounts = Set("ProductAmount")


class List(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    user = Required("User")
    products = Set(Product)


class ProductAmount(db.Entity):
    id = PrimaryKey(int, auto=True)
    product = Required("Product")
    device = Required(int)
    amount = Required(int)


class User(db.Entity):
    id = PrimaryKey(int, auto=True)
    login = Required(str, unique=True)
    password = Required(str)
    lists = Set(List)


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
                product = Product(name=name, amount=0, user=1)
    response = [dict(name=product.name, amount=product.amount)]
    return json.dumps(response)

@app.route('/lists', methods=['GET', 'POST'])
def get_lists():
    lists = []
    userId = 1
    if request.method == 'GET':
        userId = request.args.get('user_id', '')
    else:
        userId = int(request.form['user_id'])

    with db_session:
        lists = select(l.name for l in List if l.user.id == userId)[:]
    response = []
    for l in lists:
        response.append(dict(name=l));

    return json.dumps(response)

def get_all_user_products(userId):
    return select(p for p in Product if p.list.user.id == userId)[:]


def get_list_products(userId, listName):
    products = select(p for p in Product if p.list.user.id == userId and p.list.name == listName)[:]
    print products
    return products


def updateProductShop(product, productParams):
    if productParams.has_key("shopModified"):
        if productParams["shopModified"]:
            if productParams.has_key("shop"):
                productShop = productParams["shop"]
                product.shop = productShop


def updateProductPrice(product, productParams):
    if productParams.has_key("priceModified"):
        if productParams["priceModified"]:
            if productParams.has_key("price"):
                productPrice = productParams["price"]
                product.price = productPrice


@app.route('/products', methods=['GET', 'POST'])
def sync():
    products = []
    productsToBeDeleted = []
    userId = 1
    deviceId = 0
    requestContainsListName = 0
    listName = DEFAULT_LIST_NAME
    if request.method == 'GET':
        userId = request.args.get('user_id', '')
        if ('list_name' in request.args):
            requestContainsListName = 1
            listName = request.args.get('list_name', '')
    else:
        userId = int(request.form['user_id'])
        deviceId = int(request.form['device_id'])
        if ('list_name' in request.form):
            requestContainsListName = 1
            listName = request.form['list_name']
        productsJson = request.form['products']
        products = JSONDecoder().decode(productsJson)
        productsToBeDeleted = JSONDecoder().decode(request.form['productsToBeDeleted'])
        print productsToBeDeleted

    print userId
    print deviceId
    print listName

    with db_session:
        user = get(u for u in User if u.id == userId)

        for p in products:
            productList = json.loads(p)
            productParams = dict(productList)
            for key, value in productParams.items():
                print key, value
            productName = productParams["name"]
            newAmount = productParams["localAmount"]

            productListName = DEFAULT_LIST_NAME
            if productParams.has_key("list"):
                productListName = productParams["list"]

            productShop = DEFAULT_SHOP_NAME
            productPrice = 0.0

            product = get(p for p in Product if p.name == productName)
            if product is not None:
                print 'found product'
            else:
                print 'NEW PRODUCT'
                list = get(l for l in List if l.name == productListName and l.user.id == userId)
                if list is None:
                    list = List(name=productListName, user=user)
                print 'eloooo  ' + str(productPrice)
                product = Product(name=productName, amount=newAmount, list=list, price=productPrice, shop=productShop)
                # commit()
            print product.productAmounts
            updateProductAmount(deviceId, newAmount, product)
            updateProductShop(product, productParams)
            updateProductPrice(product, productParams)

        for p in productsToBeDeleted:
            productName = p[1:-1]
            product = get(p for p in Product if p.name == productName)
            for pa in product.productAmounts:
                pa.delete()
            product.delete()

    with db_session:
        user_products = get_all_user_products(userId)
        # user_products = select(p for p in Product if p.user.id == userId)[:]
        print user_products
        for p in user_products:
            amounts = select([pa.amount] for pa in ProductAmount if pa.product == p).without_distinct()
            p.amount = sum(amounts)

    response = []
    with db_session:
        if requestContainsListName > 0:
            user_products = get_list_products(userId, listName)
        else:
            user_products = get_all_user_products(userId)
        # user_products = select(p for p in Product if p.user.id == userId)[:]
        for p in user_products:
            response.append(dict(name=p.name, amount=p.amount, list=p.list.name, price=p.price, shop=p.shop))
    return json.dumps(response)


if __name__ == '__main__':
    db.generate_mapping(check_tables=True, create_tables=True)
    app.debug = True
    sql_debug(True)
    app.run(host='0.0.0.0')