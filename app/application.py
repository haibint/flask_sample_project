from flask import Flask, jsonify, render_template, request, url_for, session, flash, redirect, abort
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from helper import apology, check_money
import os
import sys
import json
from datetime import datetime
import requests
from functools import wraps # this is for login_required

from cs50 import SQL

# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///app.db")


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "GET":
        return render_template("register.html")
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
        # query database for username
        else:
            row_insertion = db.execute("INSERT INTO 'users' (username, hash, is_merchant) VALUES (:username,:new_hash,:is_merchant)", username=request.form.get("username"), new_hash=pwd_context.hash(request.form.get("password")), is_merchant=request.form.get("is_merchant"))
            return redirect(url_for("login"))
    return apology("something is wrong")


@app.route("/login", methods=["GET", "POST"])
def login():
    # """Log user in."""
    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        # redirect merchant user to their home page
        rows = db.execute("SELECT is_merchant FROM users WHERE user_id = :user_id", user_id=session["user_id"])
        if rows[0]["is_merchant"] == 1:
            return redirect(url_for("merchant"))
        if rows[0]["is_merchant"] == 0:
            return redirect(url_for("customer"))
        else:
            return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/merchant", methods=["GET", "POST"])
@login_required
def merchant_index():
    """Display the main interface a change transaction if the user is a merchant"""
    rows = db.execute("SELECT is_merchant FROM users WHERE user_id = :user_id", user_id=session["user_id"])
    if rows[0]["is_merchant"] == '2':
        return apology("sorry, you are not a merchant(jsut yet).")
    if request.method == "GET":
        return render_template("merchant_index.html")
    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        amount = request.form.get("amount")
        merchant_id = session["user_id"]
        db.execute("INSERT INTO 'records' (merchant_id,customer_id, amount) VALUES (:merchant_id, :customer_id, :amount)", merchant_id=merchant_id, customer_id=customer_id, amount=amount)
        return render_template("merchant_index.html")

@app.route("/customer", methods=["GET", "POST"])
@login_required
def customer_index():
    rows = db.execute("SELECT is_merchant, username FROM users WHERE user_id = :user_id", user_id=session["user_id"])
    if rows[0]["is_merchant"] == '1':
        return apology("Sorry, you are not logged in as a customer")
    if request.method == "GET":
        # I need to put the requested information into a list of dictionary.
        username = rows[0]['username']
        #new query from the database.
        rows = db.execute("SELECT * FROM records WHERE customer_id = :customer_id", customer_id=session["user_id"])
        total_money = 0
        for row in rows:
            total_money += row["amount"]
        customer = {
            "username":username,
            "total_money":total_money
        }
        return render_template("customer_index.html", customer=customer)
    if request.method == "POST":
        pass

# Verifying webhook for Facebook chatbot functionality.
@app.route('/verify', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/verify', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text

                    if check_money(sender_id, db) is not None:
                        message_to_send = "You have " + str(check_money(recipient_id, db)) + " dollar in your Tiny Investment account"
                        send_message(sender_id, message_to_send)
                    if check_money(sender_id, db) is None:
                        send_message(sender_id, message_to_send)

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "Hello world", 200   # this lineof code is used to let flask happy, because it want a view reponse

def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(msg, *args, **kwargs):  # simple wrapper for logging to stdout on heroku
    try:
        if type(msg) is dict:
            msg = json.dumps(msg)
        else:
            msg = str(msg).format(*args, **kwargs)
        print(u"{}: {}".format(datetime.now(), msg))
    except UnicodeEncodeError:
        pass  # squash logging errors in case of non-ascii text
    sys.stdout.flush()


app.run(host=os.getenv('IP', '0.0.0.0'),port=int(os.getenv('PORT', 8080)))

# the url
# https://tiny-investment-flask-hbtang.c9users.io:8080/