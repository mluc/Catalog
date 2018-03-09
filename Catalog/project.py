from flask import (Flask,
                   render_template,
                   request,
                   redirect,
                   jsonify,
                   url_for,
                   flash)
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catalog, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from functools import wraps
import os 
dir_path = os.path.dirname(os.path.realpath(__file__))


app = Flask(__name__)

CLIENT_ID = json.loads(
    open(dir_path + '\client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Catalog Application"

# Connect to Database and create database session
engine = create_engine('sqlite:///catalogwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        return f(*args, **kwargs)

    return decorated_function


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(dir_path + '\client_secrets.json', scope='')
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
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

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
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    flash("you are now logged in as %s" % login_session['username'])
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
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


# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Information
@app.route('/catalogs.json')
def catalogsJSON():
    catalogs = session.query(Catalog).all()
    return jsonify(catalogs=[r.serialize for r in catalogs])


@app.route('/items.json')
def itemsJSON():
    items = session.query(Item).all()
    return jsonify(items=[r.serialize for r in items])


@app.route('/catalog/<string:item_name>/item.json')
def itemJSON(item_name):
    item = session.query(Item).filter_by(name=item_name).one()
    return jsonify(item.serialize)


# Show all catalogs
@app.route('/')
def showCatalogs():
    catalogs = session.query(Catalog).order_by(asc(Catalog.name))
    items = session.query(Item).order_by(Item.time_created.desc())
    if 'username' not in login_session:
        return render_template('publiccatalogs.html',
                               catalogs=catalogs,
                               items=items)
    else:
        return render_template('catalogs.html',
                               catalogs=catalogs,
                               items=items)


# Create a new catalog
@app.route('/catalog/new/', methods=['GET', 'POST'])
@login_required
def newCatalog():
    if request.method == 'POST':
        catalog_name = request.form['name']
        existingCatalogName = \
            session.query(Catalog).filter_by(name=catalog_name).count() > 0
        if existingCatalogName:
            flash("Catalog name '%s' already existed. "
                  "Please create a different name." % catalog_name)
            return render_template('newCatalog.html',
                                   catalog_name=catalog_name)
        else:
            newCatalog = \
                Catalog(name=catalog_name, user_id=login_session['user_id'])
            session.add(newCatalog)
            flash('New Catalog %s Successfully Created' % newCatalog.name)
            session.commit()
            return redirect(url_for('showCatalogs'))
    else:
        return render_template('newCatalog.html')


# Show a catalog item
@app.route('/catalog/<string:catalog_name>/items/')
def showItems(catalog_name):
    catalogs = session.query(Catalog).order_by(asc(Catalog.name))
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    creator = getUserInfo(catalog.user_id)
    items = catalog.items
    if 'username' not in login_session:
        return render_template('publicitems.html',
                               items=items,
                               catalog=catalog,
                               catalogs=catalogs)
    else:
        return render_template('items.html',
                               items=items,
                               catalog=catalog,
                               catalogs=catalogs)


@app.route('/catalog/<string:catalog_name>/<string:item_name>/')
def showItem(catalog_name, item_name):
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    item = session.query(Item).filter_by(name=item_name).one()
    creator = getUserInfo(catalog.user_id)

    if 'username' not in login_session:
        return render_template('publicitem.html', item=item)
    else:
        return render_template('item.html', item=item)


# Create a new item item
@app.route('/catalog/item/new/', methods=['GET', 'POST'])
@login_required
def newItem():
    # pick the first catalog to check authentication
    catalog = session.query(Catalog).limit(1).first()
    catalogs = session.query(Catalog).all()

    if request.method == 'POST':
        catalog_id = int(request.form["catalog_id"])
        new_name = request.form['name']
        existingItemName = \
            session.query(Item).filter_by(name=new_name).count() > 0
        if existingItemName:  # user needs to enter a different name
            flash("Item name '%s' already existed. "
                  "Please create a different name." % new_name)
            return render_template('newitem.html',
                                   catalogs=catalogs,
                                   item_catalog_id=catalog_id,
                                   item_name=new_name,
                                   item_description=request.form['description']
                                   )
        else:  # save to database
            catalog = session.query(Catalog).filter_by(id=catalog_id).one()
            newItem = Item(name=new_name,
                           description=request.form['description'],
                           my_catalog_id=catalog_id,
                           my_catalog=catalog,
                           user_id=catalog.user_id)
            session.add(newItem)
            session.commit()
            flash('New Item %s Item Successfully Created' % (newItem.name))
            return redirect(url_for('showItems', catalog_name=catalog.name))
    else:
        return render_template('newitem.html',
                               catalogs=catalogs,
                               item_catalog_id=catalog.id)


# Edit a item item
@app.route('/catalog/<string:item_name>/edit', methods=['GET', 'POST'])
@login_required
def editItem(item_name):
    editedItem = session.query(Item).filter_by(name=item_name).one()
    catalogs = session.query(Catalog).all()
    if login_session['user_id'] != editedItem.my_catalog.user_id:
        return "<script>function myFunction() " \
               "{alert('You are not authorized to " \
               "edit items to this catalog. " \
               "Please create your own catalog " \
               "in order to edit items.');}</script>" \
               "<body onload='myFunction()''>"
    if request.method == 'POST':
        new_name = request.form['name']
        new_catalog_id = int(request.form["catalog_id"])
        new_description = request.form['description']

        existingItemName = \
            new_name != item_name and \
            session.query(Item).filter_by(name=new_name).count() > 0
        if existingItemName:  # user needs to enter a different name
            print("NO")
            flash("Item name '%s' already existed. "
                  "Please create a different name." % new_name)
            return render_template('edititem.html',
                                   catalogs=catalogs,
                                   item_catalog_id=new_catalog_id,
                                   item_name=item_name,
                                   item_description=new_description)
        else:  # save to database
            print("SAVE")
            editedItem.name = new_name
            editedItem.description = new_description
            if editedItem.my_catalog_id != new_catalog_id:
                editedItem.my_catalog_id = new_catalog_id
                editedItem.my_catalog = \
                    session.query(Catalog).filter_by(id=new_catalog_id).one()
            session.add(editedItem)
            session.commit()
            flash('Item Successfully Edited')
            return redirect(url_for('showItems',
                                    catalog_name=editedItem.my_catalog.name))
    else:
        return render_template('edititem.html',
                               catalogs=catalogs,
                               item_catalog_id=editedItem.my_catalog_id,
                               item_name=editedItem.name,
                               item_description=editedItem.description)


# Delete a item item
@app.route('/catalog/<string:item_name>/delete', methods=['GET', 'POST'])
@login_required
def deleteItem(item_name):
    itemToDelete = session.query(Item).filter_by(name=item_name).one()
    if login_session['user_id'] != itemToDelete.my_catalog.user_id:
        return "<script>function myFunction() " \
               "{alert('You are not authorized to " \
               "delete items to this catalog. " \
               "Please create your own catalog " \
               "in order to delete items.');}</script>" \
               "<body onload='myFunction()''>"

    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Item Successfully Deleted')
        return redirect(url_for('showItems',
                                catalog_name=itemToDelete.my_catalog.name))
    else:
        return render_template('deleteItem.html', item=itemToDelete)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']

        del login_session['username']
        del login_session['email']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalogs'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalogs'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
