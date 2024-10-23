import requests
from functools import wraps
import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

import datetime

import mysql.connector

db = mysql.connector.connect( 
    host = "localhost", 
    user = "root", 
    password = "SQLSteph923", 
    database = "library" )

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(keyword):
    """Look up book for keyword."""
    url = f"https://library504.io/quote?keyword={keyword.upper()}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP error responses
        book_data = response.json()
        return {
            "title": book_data["bookTitle"],
            "author": book_data["bookAuthor"],
            "year": book_data["publishYear"],
            "edition": book_data["printEdition"],
            "copies": book_data["numCopies"]
        }
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except (KeyError, ValueError) as e:
        print(f"Data parsing error: {e}")
    return None

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():  
    """Log user in"""
    session.clear() # Forget any user_id
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM reader WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if password == "" or confirmation == "" or username == "":
            return apology("missing field", 400)

        if password != confirmation:
            return apology("password and confirmation don't match", 400)

        taken = db.execute("SELECT * FROM reader WHERE username = ?", username)

        if len(taken) >= 1:
            return apology("username already taken", 400)
        else:
            hash = generate_password_hash(password)
            result = db.execute("INSERT INTO reader (username, hash) VALUES(?, ?)", username, hash)
            session["id"] = result
            return redirect("/")

    else:
        return render_template("register.html")

@app.route("/")
@login_required
def index():
    """Homepage"""
    #get the latest books 
    latest = db.execute("SELECT title, author, year, edition FROM books INNER JOIN history ON books.id = history.readerid WHERE readerid = ? ORDER BY date DESC LIMIT 5", session["id"])
    return render_template("index.html", latest=latest) 

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
     """Search using a keyword"""
     if request.method == "POST":
        keyword = request.form.get("keyword")
        results = db.execute("SELECT * FROM books WHERE id LIKE '%?%' OR title LIKE '%?%' OR author LIKE '%?%' OR year LIKE '%?%' OR genre LIKE '%?%' OR topicsA like '%?%' OR topicsB like '%?%' OR topicsC like '%?%'", keyword)
        # display search results
        return render_template("results.html", keyword=keyword, results=results)
     
     else:
        return render_template("search.html")

@app.route("/browse", methods=["GET", "POST"])
@login_required
def browse():
    """Browse the collection"""
    books = db.execute("SELECT * FROM books ORDER BY author")
    return render_template("browse.html", books=books)


@app.route("/log", methods=["GET", "POST"]) #to do
@login_required
def log():
    """Log a new book into library"""
    if request.method == "POST":
        title = request.form.get("title")
        authorfirst = request.form.get("authorfirst")
        authorlast = request.form.get("authorlast")
        year = request.form.get("year")
        edition = request.form.get("edition")
        copies = request.form.get("copies")
        genre = request.form.get("checkedValues")
        topicsA = request.form.get("topicsA")
        topicsB = request.form.get("topicsB")
        topicsC = request.form.get("topicsC")
        
        exist = db.execute("SELECT * from books where title = title AND authorfirstname = authorfirst AND authorlastname = authorlast AND year = year AND edition = edition")

        if len(exist) >=1:
            return apology("Bookbook already logged", 400)
        else:
            db.execute("INSERT INTO books (title, authorfirstname, authorlastname, year, edition, copies, genre, topicsA, topicsB, topicsC) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", title, authorfirst, authorlast, year, edition, copies, genre, topicsA, topicsB, topicsC)
            bookid = db.execute("SELECT SCOPE_IDENTITY()")
            action = str("logged")
            db.execute("INSERT INTO history (bookid, readerid, action) VALUES (?, ?, ?)", bookid, session["id"], action)
    else:
        return render_template("log.html")
    
@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    """Display session history of logged in user"""
    history = db.execute("SELECT bookID, action, date, time FROM history WHERE readerID = ?", session["id"])

    return render_template("history.html", history=history)
    
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")