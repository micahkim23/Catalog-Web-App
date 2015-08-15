from flask import Flask, render_template, request, redirect, url_for, flash, jsonify  # noqa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from catalogusers_setup import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
        open('client_secrets.json', 'r').read())['web']['client_id']

engine = create_engine('sqlite:///catalogwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# home page that lists all the categories
@app.route('/')
def categoryHomePage():
    categories = session.query(Category).all()
    if 'username' not in login_session:
        return render_template('publicCategory.html', categories=categories) 
    else:
        return render_template('category.html', categories=categories)  


# Create a state token to prevent request forgery.
# Store it in the session for later validation.
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))  # noqa
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)  # noqa
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '  # noqa
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        flash("Current user not connected.")
        return redirect(url_for('categoryHomePage'))
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash("You have been successfully logged out.")
        return redirect(url_for('categoryHomePage'))
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        flash("Failed to revoke token for given user.")
        return redirect(url_for('categoryHomePage'))


# lists items of given category
@app.route('/catalog/<int:cat_id>/items/')
def categoryItems(cat_id):
    categories = session.query(Category).all()
    cat = session.query(Category).filter_by(id=cat_id).one()
    items = session.query(Item).filter_by(cat_id=cat_id)
    creator = getUserInfo(cat.user_id)
    numOfItems = 0
    store = ''
    for i in items:
        numOfItems += 1
    if numOfItems == 1:
	store += str(numOfItems) + " item"
    else:
	store += str(numOfItems) + " items"
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicItems.html', categories=categories, category=cat, items=items, numOfItems=store, login_session=login_session)  # noqa
    else:
        return render_template('items.html', categories=categories, category=cat, items=items, numOfItems=store)  # noqa


# description of item in given category
@app.route('/catalog/<int:cat_id>/<int:item_id>/')
def itemDescription(item_id, cat_id):
    category = session.query(Category).filter_by(id=cat_id).one()
    item = session.query(Item).filter_by(cat_id=cat_id, id=item_id).one()
    creator = getUserInfo(category.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicItemDescription.html', item=item, login_session=login_session)  #noqa
    else:
        return render_template('itemDescription.html', item=item, category=category)  # noqa


# json link for catalog app
@app.route('/catalog.json')
def catalogJson():
    catalog = session.query(Category).all()
    store = []
    index = 0
    for c in catalog:
	store.append(c.serialize)
	items = session.query(Item).filter_by(cat_id=c.id)
	store[index]['Item'] = []
	for i in items:
	    store[index]['Item'].append(i.serialize)
	if len(store[index]['Item']) == 0:
	    store[index].pop('Item', None)
	index += 1
    return jsonify(Category=store)


# link to delete item
@app.route('/catalog/<int:cat_id>/<int:item_id>/delete', methods=['GET', 'POST'])
def deleteItem(item_id, cat_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=cat_id).one()
    itemToDelete = session.query(Item).filter_by(cat_id=cat_id, id=item_id).one()  # noqa
    if category.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this item. Please create your own item in order to delete.');}</script><body onload='myFunction()''>"  # noqa
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash(category.name + " Item Successfully Deleted")
        return redirect(url_for('categoryItems', cat_id=category.id))
    else:
        return render_template('deleteCatalogItem.html', item=itemToDelete)  # noqa


# link to edit item
@app.route('/catalog/<int:cat_id>/<int:item_id>/edit', methods=['GET', 'POST'])
def editItem(item_id, cat_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=cat_id).one()
    editedItem = session.query(Item).filter_by(cat_id=cat_id, id=item_id).one()  # noqa
    if category.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this item. Please create your own item in order to edit.');}</script><body onload='myFunction()''>"  # noqa
    if request.method == 'POST':
        if request.form['name']:
            editedItem.title = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        session.add(editedItem)
        session.commit()
        flash(category.name + " Item Successfully Edited")
        return redirect(url_for('categoryItems', cat_id=category.id))  # noqa
    else:
	return render_template('editCatalogItem.html', item=editedItem)  # noqa


# link to add new item
@app.route('/catalog/item/add', methods=['GET', 'POST'])
def addItem():
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).all()
    if request.method == 'POST':
        cat_name = request.form['category']
        category = session.query(Category).filter_by(name=cat_name).one()  # noqa
        newItem = Item(title=request.form['name'], description=request.form['description'], cat_id=category.id, user_id=category.user_id)  # noqa
        session.add(newItem)
        session.commit()
        flash("New Item " + newItem.title + " Successfully Created")
        return redirect(url_for('categoryItems', cat_id=category.id))
    else:
        return render_template('addCatalogItem.html', categories=categories, login_session=login_session)  # noqa


@app.route('/catalog/category/add', methods=['GET', 'POST'])
def addCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(name=request.form['name'], user_id=login_session['user_id'])  # noqa
        session.add(newCategory)
        session.commit()
        flash("New Category " + newCategory.name + " Successfully Created")  # noqa
        return redirect(url_for('categoryHomePage'))
    else:
         return render_template('addCategory.html')  # noqa


@app.route('/catalog/<int:cat_id>/delete', methods=['GET', 'POST'])
def deleteCategory(cat_id):
    if 'username' not in login_session:
        return redirect('/login')
    categoryToDelete = session.query(Category).filter_by(id=cat_id).one()  # noqa
    if categoryToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this category. Please create your own category in order to delete.');}</script><body onload='myFunction()''>"  # noqa
    if request.method == 'POST':
        session.delete(categoryToDelete)
        session.commit()
        flash(categoryToDelete.name + " Category Successfully Deleted")
        return redirect(url_for('categoryHomePage'))
    else:
        return render_template('deleteCategory.html', category=categoryToDelete)  # noqa


@app.route('/catalog/<int:cat_id>/edit', methods=['GET', 'POST'])
def editCategory(cat_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedCategory = session.query(Category).filter_by(id=cat_id).one()
    if editedCategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this category. Please create your own category in order to edit.');}</script><body onload='myFunction()''>"  # noqa
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
        session.add(editedCategory)
        session.commit()
        flash("Category Successfully Edited " + editedCategory.name)
        return redirect(url_for('categoryHomePage'))
    else:
        return render_template('editCategory.html', category=editedCategory)  # noqa


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session['email'], picture=login_session['picture'])  # noqa
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()  # noqa
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# __main__ is run when python application.py is called from command line
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
