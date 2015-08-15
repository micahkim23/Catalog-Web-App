This is the README.txt file for the catalog app that allows users to create/delete/update items and categories from a database on a locally hosted website.

This app is run on:
python version: 2.7.6
flask: 0.9 
sqlalchemy: 1.0

If your version of flask is not up to date, run the following in the command line:
sudo pip install werkzeug==0.8.3
sudo pip install flask==0.9
sudo pip install Flask-Login==0.1.3

This will get rid of the error: OAuth2Credentials object is not JSON serializable.

list of endpoints:
http://localhost:8000/												
(homepage with list of categories)
http://localhost:8000/login  										
(login page with google plus sign in)
http://localhost:8000/gconnect 										
(logs you into google plus)
http://localhost:8000/gdisconnect 									
(logs you out)
http://localhost:8000/catalog.json 									
(json endpoint)
http://localhost:8000/catalog/<int:cat_id>/items 					
(shows items of a particular category)
http://localhost:8000/catalog/<int:cat_id>/<int:item_id> 			
(shows description of a particular item)
http://localhost:8000/catalog/<int:cat_id>/<int:item_id>/delete 	
(delete an item)
http://localhost:8000/catalog/<int:cat_id>/<int:item_id>/edit 		
(edit an item)
http://localhost:8000/catalog/item/add 								
(add a new item)
http://localhost:8000/catalog/<int:cat_id>/delete 					
(delete a category)
http://localhost:8000/catalog/<int:cat_id>/edit 					
(edit a category)
http://localhost:8000/catalog/category/add 							
(add a new category)

1. While in the virtual machine, change directories to /vagrant/catalog. To set up the database, you have to type python catalog_setup.py in the command line. This will set up the database of items and categories. Type in python application.py into the command line to get the server running at http://localhost:8000/.

2. I used sqlalchemy to create the database and call queries to represent my data. I used flask to set up the web framework that deals with the various pages and links of the website. I also used google sign-in OAuth 2.0 authentication to check if users were signed in before allowing them to make changes to the database. An API Endpoint was used to display the database data in JSON. The website is a RESTful web application that implements CRUD operations. This app also uses local authorization, so that users can only modify their own items.