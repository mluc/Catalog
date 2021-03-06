# Build an Item Catalog Application
This is a content management system using Flask framework in Python to provide a list of items within categories. Google authentication is used via OAuth 2.0. All data is stored in SQLite database. SQLAlchemy is used as ORM.
* Setup:
    * *virtualenv venv36*
    * *venv36\Scripts\activate* (for Windows)
    * *pip install -r requirements.txt* to install all the required packages
    * *cd Catalog* to go the Catalog folder
    * *python database_setup.py* to setup database (OPTIONAL)
    * *python lotsofitems.py* to save some data to database (OPTIONAL)
    * *python project.py* to start
* Open a browser:
  * *http://localhost:5000* to go to home page
  * *http://localhost:5000/catalogs.json* to show all catalogs in json
  * *http://localhost:5000/items.json* to show all items in json
  * *http://localhost:5000/catalog/Snowboard/item.json* to show 1 item named Snowboard (if exist)
* Troubleshoot:
    * Only run python lotsofitems.py once
    * sqlalchemy.orm.exc.MultipleResultsFound: delete catalogwithusers.db then run *python database_setup.py* and *python lotsofitems.py* again

