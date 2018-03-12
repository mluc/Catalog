import json
import os
import random
import string
from functools import wraps

from flask import (Flask,
                   render_template,
                   request,
                   redirect,
                   jsonify,
                   url_for,
                   flash)
from flask import session as login_session
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker

from facebook_login import (facebook_api, fbdisconnect)
from google_login import (google_api, gdisconnect)

from database_setup import Base, Catalog, Item, User

app = Flask(__name__)
app.register_blueprint(google_api)
app.register_blueprint(facebook_api)

dir_path = os.path.dirname(os.path.realpath(__file__))

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
        elif login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']

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
