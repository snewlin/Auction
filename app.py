from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import hashlib
import pandas as pd
import re
import random
import uuid
import datetime
import csv

# TODO:  create pages for items, helpdesk, create pages for sellers
# Plan of action: Profile functions first, then work on helpdesk, then work on bids/transactions
# 4/17: FIX zipcode!!!!!
# 4/18: helpdesk done, do bids stuff???
# 4/19: Seller pages
# 4/20: Item pages/ front page
# 4/21: Figure out what to do about vendors and categories!!!!

app = Flask(__name__)
app.secret_key = 'some_secret_key'

# Connect to database
con = sqlite3.connect('database.db')
c = con.cursor()

# creating the users,bidders,sellers, CC table if it does not exist
c.execute('''CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    password TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS bidders (
                    email TEXT PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    gender TEXT,
                    age INTEGER,
                    home_address_id TEXT,
                    major TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS sellers (
                    email TEXT PRIMARY KEY,
                    bank_num TEXT,
                    bank_account TEXT,
                    balance REAL
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS local_vendors (
                    email TEXT PRIMARY KEY,
                    business_name TEXT,
                    business_address_id TEXT,
                    customer_service_phone TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS credit_cards (
                    credit_card_num TEXT PRIMARY KEY,
                    card_type TEXT,
                    expire_month INTEGER,
                    expire_year INTEGER,
                    security_code TEXT,
                    owner_email TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS address (
                    address_id TEXT PRIMARY KEY,
                    zipcode TEXT,
                    street_num TEXT,
                    street_name TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS zipcode_info (
                    zipcode TEXT PRIMARY KEY,
                    city TEXT,
                    state TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS categories (
                    category_name TEXT PRIMARY KEY,
                    parent_category TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS auction_listings (
                    seller_email TEXT,
                    listing_id TEXT,
                    category TEXT,
                    auction_title TEXT,
                    product_name TEXT,
                    product_description TEXT,
                    quantity INTEGER,
                    reserve_price REAL,
                    max_bids INTEGER,
                    status TEXT,
                    PRIMARY KEY (seller_email, listing_id)
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS bids (
                    bid_id TEXT PRIMARY KEY,
                    seller_email TEXT,
                    listing_id TEXT,
                    bidder_email TEXT,
                    bid_price REAL
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                    transaction_id TEXT PRIMARY KEY,
                    seller_email TEXT,
                    listing_id TEXT,
                    buyer_email TEXT,
                    date DATETIME,
                    payment TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS rating (
                    bidder_email TEXT,
                    seller_email TEXT REFERENCES sellers(email),
                    date DATETIME,
                    rating INTEGER,
                    rating_desc TEXT,
                    PRIMARY KEY (bidder_email, date)
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS helpdesk (
                    email TEXT PRIMARY KEY,
                    position TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    sender_email TEXT,
                    helpdesk_staff_email TEXT,
                    request_type TEXT,
                    request_desc TEXT,
                    request_status TEXT
                    )''')
c.execute('''CREATE TABLE IF NOT EXISTS notifications (
                    notification_id TEXT PRIMARY KEY,
                    email TEXT,
                    notif_title TEXT,
                    notif_bid TEXT,
                    notif_type TEXT,
                    notif_action TEXT
                    )''')
# Read CSV file into dataframe
df = pd.read_csv('Users.csv')

# # Iterate through rows of dataframe
for i, row in df.iterrows():
    # Get email and password from row
    email = row['email']
    password = row['password']

    # Hash password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    # Checking if the users already exist
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()
    # Insert data into database if user does not exist
    if not user:
        c.execute("INSERT INTO users (email, password) VALUES (?,?)", (email, hashed_password))

con.commit()

# Close connection
con.close()


@app.route('/')
def home():
    # connecting to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # getting categories for the home page browsing
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()

    # getting the top sellers for the front page
    cc.execute('SELECT seller_email, AVG(rating) FROM rating GROUP BY seller_email ORDER BY AVG(rating) DESC LIMIT 20')
    top_sellers = cc.fetchall()
    top_sellers_emails = [seller[0] for seller in top_sellers]
    cc.execute(
        'SELECT * FROM auction_listings WHERE seller_email IN ({}) AND status = 1 ORDER BY RANDOM() LIMIT 20'.format(
            ','.join(['?'] * len(top_sellers_emails))), top_sellers_emails)
    listings = cc.fetchall()
    conn.close()
    if 'email' in session:

        # connected to DB if user is logged in
        conn = sqlite3.connect('database.db')
        cc = conn.cursor()

        # getting the email for seller check
        email_check = session['email']
        cc.execute("SELECT * FROM sellers WHERE email=?", (email_check,))
        seller = cc.fetchone()

        # getting the notifications and notification count for navigation
        cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (email_check, 'closed'))
        notifications = cc.fetchall()
        cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (email_check, 'closed'))
        unread_notification_count = cc.fetchone()[0]
        if unread_notification_count:
            has_unread_notifications = True
        else:
            has_unread_notifications = False
        conn.close()

        # returning seller page if seller
        if seller:
            return render_template('home.html', email=session['email'], logged_in=True, seller=True,
                                   categories=categories, listings=listings, notifications=notifications,
                                   has_unread_notifications=has_unread_notifications,
                                   unread_notification_count=unread_notification_count)
        # otherwise returning user page
        else:
            return render_template('home.html', email=session['email'], logged_in=True, seller=False,
                                   categories=categories, listings=listings, notifications=notifications,
                                   has_unread_notifications=has_unread_notifications,
                                   unread_notification_count=unread_notification_count)
    # returning non logged in user
    else:
        return render_template('home.html', logged_in=False, categories=categories, listings=listings)


# sign up function
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # checking request method
    if request.method == 'POST':
        # getting email and password from forms, then hashing password
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # getting form info
        first_name = request.form['firstname']
        last_name = request.form['lastname']
        major = request.form['major']
        gender = request.form['gender']
        age = request.form['age']
        street_num = request.form['street_num']
        street_name = request.form['street_name']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']
        credit_card_num = request.form['credit_card_num']
        card_type = request.form['card_type']
        expire_month = request.form['expire_month']
        expire_year = request.form['expire_year']
        security_code = request.form['security_code']

        # checking the values for CC info and zipcode
        if not re.match(r'\d{4}', expire_year):
            return render_template('signup.html', error='Invalid expire year.')
        if not re.match(r'\d{3}', security_code) or re.match(r'\d{4}', security_code):
            return render_template('signup.html', error='Invalid security code.')
        if not re.match(r'\d{5}', zipcode):
            return render_template('signup.html', error='Invalid zipcode.')

        # checking user is a student
        if not email.endswith("@lsu.edu"):
            return render_template('signup.html',
                                   error='Must be an LSU email. Please contact the helpdesk for more help.')

        # creating a home address_id
        home_address_id = random.randint(100000, 999999)

        # connecting to database
        conn = sqlite3.connect('database.db')
        cc = conn.cursor()

        # checking user doesnt already exist
        cc.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cc.fetchone()

        # error if user already exists
        if user:
            return render_template('signup.html', error='User already exists. Please log in or try a new email.')

        # putting the new user into the database
        cc.execute("INSERT INTO users VALUES (?,?)", (email, hashed_password))

        cc.execute("INSERT INTO bidders VALUES (?,?,?,?,?,?,?)",
                   (email, first_name, last_name, gender, age, home_address_id, major))

        cc.execute("INSERT INTO address VALUES (?,?,?,?)", (home_address_id, zipcode, street_num, street_name))

        cc.execute("INSERT INTO credit_cards VALUES (?,?,?,?,?,?)",
                   (credit_card_num, card_type, expire_month, expire_year, security_code, email))

        # checking the zipcode doesnt already exist
        cc.execute("SELECT * FROM zipcode_info WHERE zipcode=?", (zipcode,))

        zips = cc.fetchone()
        # if the zipcode doesnt exist
        if not zips:
            cc.execute("INSERT INTO zipcode_info VALUES (?,?,?)", (zipcode, city, state))

        # committing change
        conn.commit()
        session['email'] = email

        # redirect home
        return redirect('/')
    else:
        # rendering the page without login
        conn = sqlite3.connect('database.db')
        cc = conn.cursor()
        cc.execute("SELECT category_name FROM categories")
        categories = cc.fetchall()
        return render_template('signup.html', categories=categories, logged_in=False)


# login function
@app.route('/login', methods=['GET', 'POST'])
def login():
    # checking request method
    if request.method == 'POST':
        # receiving email and password from form, hashing the password
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # connecting to database and finding the user
        conn = sqlite3.connect('database.db')
        cc = conn.cursor()
        cc.execute("SELECT * FROM users WHERE email=? AND password=?", (email, hashed_password))
        user_login = cc.fetchone()

        # if the user exists, going to home page
        if user_login:
            session['email'] = email
            return redirect('/')

        # if the user does not exist, get an error message
        else:
            # if email and password don't match, show error message
            return render_template("login.html", error="Invalid email or password.")

    # rendering unlogged in
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    return render_template('login.html', error=None, categories=categories, logged_in=False)


# profile function
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # making user sign in if not signed in
    if 'email' not in session:
        return redirect('/login')

    # getting the session
    email = session['email']

    # connecting to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # getting the user info for profile
    cc.execute('''SELECT b.first_name, b.last_name, b.email, b.gender, b.age, a.street_num, a.street_name, z.city, z.state, a.zipcode, b.major
                         FROM bidders b JOIN address a ON b.home_address_id = a.address_id JOIN zipcode_info z ON a.zipcode = z.zipcode
                         WHERE b.email = ?''', (email,))
    user_info = cc.fetchone()

    # getting seller info if seller
    cc.execute('''SELECT email, bank_num, bank_account, balance FROM sellers WHERE email = ?''', (email,))
    seller_info = cc.fetchone()

    # getting vendor info if vendor
    cc.execute('''SELECT * FROM local_vendors WHERE email=?''', (email,))
    vendor_info = cc.fetchone()

    # getting vendor address
    if vendor_info:
        vendor_address = vendor_info[2]
        cc.execute(
            '''SELECT a.street_num, a.street_name, z.city, z.state, a.zipcode from address a JOIN zipcode_info z ON a.zipcode = z.zipcode WHERE address_id = ?''',
            (vendor_address,))
        address_info = cc.fetchone()
    else:
        address_info = None

    # returning the categories for navigation
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()

    # getting the notifications for navigation
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

    # getting the bought items
    cc.execute("""
                SELECT auction_listings.product_name, transactions.payment, transactions.seller_email
                FROM auction_listings
                JOIN transactions ON auction_listings.seller_email = transactions.seller_email
                WHERE transactions.buyer_email = ?
            """, (email,))
    bought_items = cc.fetchall()

    # getting the open bids
    cc.execute("""
        SELECT a.product_name, b.bid_price, a.listing_id
        FROM auction_listings a
        JOIN bids b ON a.listing_id = b.listing_id
        JOIN (
          SELECT listing_id, MAX(bid_price) AS max_bid_price
          FROM bids
          WHERE bidder_email = ?
          GROUP BY listing_id
        ) c ON b.listing_id = c.listing_id AND b.bid_price = c.max_bid_price
        WHERE a.status = 1
    """, (email,))
    open_bids = cc.fetchall()

    # getting closed bids
    cc.execute("""
            SELECT a.product_name, b.bid_price, a.listing_id
            FROM auction_listings a
            JOIN bids b ON a.listing_id = b.listing_id
            JOIN (
              SELECT listing_id, MAX(bid_price) AS max_bid_price
              FROM bids
              WHERE bidder_email = ?
              GROUP BY listing_id
            ) c ON b.listing_id = c.listing_id AND b.bid_price = c.max_bid_price
            WHERE a.status = 2 or a.status = 1
        """, (email,))
    closed_bids = cc.fetchall()

    # if seller
    if seller_info:

        # getting sold items
        cc.execute("""
            SELECT auction_listings.product_name, transactions.payment
            FROM auction_listings
            JOIN transactions ON auction_listings.seller_email = transactions.seller_email
            WHERE auction_listings.seller_email = ?
        """, (email,))
        # retrieve the results as a list of tuples
        sold_items = cc.fetchall()

        # returning template with bought, sold, bids, closed
        return render_template('profile.html', user_info=user_info, seller_info=seller_info, seller=True,
                               categories=categories, notifications=notifications, sold_items=sold_items,
                               bought_items=bought_items, unread_notification_count=unread_notification_count,
                               has_unread_notifications=has_unread_notifications, logged_in=True, open_bids=open_bids,
                               closed_bids=closed_bids, vendor_info=vendor_info, address_info=address_info)
    # render profile template with user's information
    else:

        # returing everything but sold items and making seller false
        return render_template('profile.html', user_info=user_info, seller=False, categories=categories,
                               notifications=notifications, bought_items=bought_items,
                               unread_notification_count=unread_notification_count,
                               has_unread_notifications=has_unread_notifications, logged_in=True, open_bids=open_bids,
                               closed_bids=closed_bids)


@app.route('/profile/update', methods=['GET', 'POST'])
def profile_update():
    # get user's email from session
    email = session['email']

    # getting DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # finding out if user is a vendor
    cc.execute('''SELECT *
                                FROM local_vendors
                                WHERE email = ?''', (email,))
    vendor = cc.fetchone()

    # getting request
    if request.method == 'POST':

        # checking if user is a vendor
        cc.execute('''SELECT *
                                            FROM local_vendors
                                            WHERE email = ?''', (email,))
        vendor = cc.fetchone()

        # checking if user is seller
        cc.execute('''SELECT *
                                            FROM sellers
                                            WHERE email = ?''', (email,))
        seller = cc.fetchone()

        # getting items from the form
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        street_num = request.form['street_num']
        street_name = request.form['street_name']
        zipcode = request.form['zipcode']
        city = request.form['city']
        state = request.form['state']

        # checking items if vendor or seller
        if vendor or seller:
            bank_num = request.form['bank_num']
            bank_account = request.form['bank_account']

        # otherwise set to none
        else:
            bank_num = None
            bank_account = None

        # getting vendor items
        if vendor:
            business_name = request.form['business_name']
            customer_service_phone = request.form['customer_service_phone']

        # otherwise set to none
        else:
            business_name = None
            customer_service_phone = None

        # if user is not a vendor, first name, last name, major, or age other wise set to None
        if not vendor:
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            major = request.form['major']
            age = request.form['age']
        else:
            first_name = None
            last_name = None
            major = None
            age = None

        # getting the business ID for vendor otherwise just look through
        if vendor:
            cc.execute('''SELECT business_address_id
                                             FROM local_vendors
                                             WHERE email = ?''', (email,))
            address_id = cc.fetchone()[0]
        else:
            cc.execute('''SELECT home_address_id
                                     FROM bidders
                                     WHERE email = ?''', (email,))
            address_id = cc.fetchone()[0]

        # update user's information in database

        # changing password, error if confirmed password doesnt match
        if password:
            if not password_confirm:
                return render_template("profile_update.html", error="Please confirm your new password.")
            if password != password_confirm:
                return render_template("profile_update.html", error="Please make sure your passwords match.")

            # hashing password
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            # update
            cc.execute('''UPDATE users
                          SET password = ?
                          WHERE email = ?''', (hashed_password, email))
        # changing name
        if first_name:
            cc.execute('''UPDATE bidders
                          SET first_name = ?
                          WHERE email = ?''', (first_name, email))
        if last_name:
            cc.execute('''UPDATE bidders
                          SET last_name = ?
                          WHERE email = ?''', (last_name, email))

        # changing age
        if age:
            cc.execute('''UPDATE bidders
                          SET age = ?
                          WHERE email = ?''', (age, email))
        # changing major
        if major:
            cc.execute('''UPDATE bidders
                          SET major = ?
                          WHERE email = ?''', (major, email))

        # chaning street
        if street_num:
            cc.execute('''UPDATE address
                          SET street_num = ?
                          WHERE address_id = ?''', (street_num, address_id))
        if street_name:
            cc.execute('''UPDATE address
                          SET street_name = ?
                          WHERE address_id = ?''', (street_name, address_id))

        # updating user's zipcode, will not update zipcode table unless zipcode DNE
        if zipcode:
            if not re.match(r'\d{5}', zipcode):
                return render_template('profile_update.html', error='Invalid zipcode.')
            cc.execute('''UPDATE address
                          SET zipcode = ?
                          WHERE address_id = ?''', (zipcode, address_id))

            cc.execute('''SELECT COUNT(*) FROM zipcode_info WHERE zipcode=?''', (zipcode,))
            count = cc.fetchone()[0]

            if count == 0:
                # If the zipcode doesn't exist, insert a new row into the zipcode_info table
                cc.execute('''INSERT INTO zipcode_info (zipcode, city, state) VALUES (?, ?, ?)''',
                           (zipcode, city, state))
            else:
                # If the zipcode already exists, update the city and state values
                cc.execute('''UPDATE zipcode_info SET city=?, state=? WHERE zipcode=?''', (city, state, zipcode))

        # updating bank num and account
        if bank_num:
            cc.execute('''UPDATE sellers
                                SET bank_num = ?
                                WHERE email = ?''', (bank_num, email))
        if bank_account:
            cc.execute('''UPDATE sellers
                                SET bank_account = ?
                                WHERE email = ?''', (bank_account, email))

        # updating business name and phone for vendors
        if business_name:
            cc.execute('''UPDATE local_vendors
                                SET business_name = ?
                                WHERE email = ?''', (business_name, email))
        if customer_service_phone:
            cc.execute('''UPDATE local_vendors
                                SET customer_service_phone = ?
                                WHERE email = ?''', (customer_service_phone, email))
        conn.commit()

        # redirect user to profile page
        return redirect('/profile')

    # getting notifs, categories and seller info if they are
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False
    cc.execute('''SELECT *
                        FROM sellers
                        WHERE email = ?''', (email,))
    seller = cc.fetchone()

    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()

    # rendering seller page
    if seller:
        return render_template('profile_update.html', seller_check=True, categories=categories,
                               notifications=notifications, unread_notification_count=unread_notification_count,
                               has_unread_notifications=has_unread_notifications, logged_in=True, vendor=vendor)
    else:
        # render profile_update template with user's information
        return render_template('profile_update.html', seller_check=False, categories=categories,
                               notifications=notifications, unread_notification_count=unread_notification_count,
                               has_unread_notifications=has_unread_notifications, logged_in=True)


# credit cards
@app.route('/credit_cards', methods=['GET', 'POST'])
def credit_cards():
    # getting session
    email = session['email']

    # connect to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # checking seller
    cc.execute('''SELECT *
                            FROM sellers
                            WHERE email = ?''', (email,))
    seller = cc.fetchone()
    if seller:
        seller = True
    else:
        seller = False

    # getting current CC info
    cc.execute(
        "SELECT credit_card_num, card_type, expire_month, expire_year, security_code FROM credit_cards WHERE owner_email=?",
        (email,))
    cards = cc.fetchall()

    # getting categories and notifications for navigation
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False
    if request.method == 'POST':
        # Get the form data from the request
        card_num = request.form['card_num']
        card_type = request.form['card_type']
        expire_month = request.form['expire_month']
        expire_year = request.form['expire_year']
        security_code = request.form['security_code']
        action = request.form['action']

        # checking security code is valid
        if not re.match(r'\d{3}', security_code) or re.match(r'\d{4}', security_code):
            return render_template('credit_cards.html', error='Invalid security code.', cards=cards, seller=seller,
                                   categories=categories, notifications=notifications,
                                   unread_notification_count=unread_notification_count,
                                   has_unread_notifications=has_unread_notifications, logged_in=True)

        # Perform the appropriate action based on the form data
        if action == 'add':
            # Add a new credit card to the database
            cc.execute(
                "INSERT INTO credit_cards (credit_card_num, card_type, expire_month, expire_year, security_code, owner_email) VALUES (?, ?, ?, ?, ?, ?)",
                (card_num, card_type, expire_month, expire_year, security_code, email))
            conn.commit()

            # getting new set of cards with card added
            cc.execute(
                "SELECT credit_card_num, card_type, expire_month, expire_year, security_code FROM credit_cards WHERE owner_email=?",
                (email,))
            cards = cc.fetchall()
            message = 'Credit card added successfully!'
            return render_template('credit_cards.html', message=message, cards=cards, seller=seller,
                                   categories=categories, notifications=notifications,
                                   unread_notification_count=unread_notification_count,
                                   has_unread_notifications=has_unread_notifications, logged_in=True)
        elif action == 'delete':
            # Delete an existing credit card from the database
            cc.execute("DELETE FROM credit_cards WHERE credit_card_num=?", (card_num,))
            conn.commit()

            # getting new cards set for user
            cc.execute(
                "SELECT credit_card_num, card_type, expire_month, expire_year, security_code FROM credit_cards WHERE owner_email=?",
                (email,))
            cards = cc.fetchall()
            message = 'Credit card deleted successfully!'
            return render_template('credit_cards.html', message=message, cards=cards, seller=seller,
                                   categories=categories, notifications=notifications,
                                   unread_notification_count=unread_notification_count,
                                   has_unread_notifications=has_unread_notifications, logged_in=True)
        else:
            cc.execute(
                "SELECT credit_card_num, card_type, expire_month, expire_year, security_code FROM credit_cards WHERE owner_email=?",
                (email,))
            cards = cc.fetchall()
            error = 'Invalid action specified!'
            return render_template('credit_cards.html', error=error, cards=cards, seller=seller, categories=categories,
                                   notifications=notifications, unread_notification_count=unread_notification_count,
                                   has_unread_notifications=has_unread_notifications, logged_in=True)

    # Retrieve the list of credit cards from the database and display them to the user

    return render_template('credit_cards.html', cards=cards, seller=seller, categories=categories,
                           notifications=notifications, unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications, logged_in=True)

# seller's personal page
@app.route('/seller_page', methods=['GET', 'POST'])
def seller_page():
    if 'email' not in session:
        return redirect('/login')
    # getting email
    seller_email = session['email']

    # connecting to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # getting vendor info if one
    cc.execute('SELECT * FROM local_vendors WHERE email = ?', (seller_email,))
    vendor_info = cc.fetchone()

    # getting ratings info
    cc.execute('SELECT * FROM rating WHERE seller_email = ?', (seller_email,))
    ratings = cc.fetchall()

    # getting user info
    cc.execute('SELECT * FROM bidders WHERE email = ?', (seller_email,))
    user_info = cc.fetchone()

    # finding open listing info
    cc.execute(
        'SELECT auction_title, product_name, product_description,reserve_price,listing_id FROM auction_listings WHERE seller_email = ? and status = 1',
        (seller_email,))
    open_listings = cc.fetchall()

    # getting closed listing info
    cc.execute(
        'SELECT auction_title, product_name, product_description,reserve_price,listing_id FROM auction_listings WHERE seller_email = ? and status = 0',
        (seller_email,))
    closed_listings = cc.fetchall()

    # getting sold listing info
    cc.execute(
        'SELECT auction_title, product_name, product_description,reserve_price,listing_id FROM auction_listings WHERE seller_email = ? and status = 2',
        (seller_email,))
    sold_listings = cc.fetchall()

    # getting the rating in stars for user
    cc.execute('SELECT AVG(rating) FROM rating WHERE seller_email = ?', (seller_email,))
    rating_avg = cc.fetchone()[0]
    stars = int(round(rating_avg)) if rating_avg is not None else 0

    # getting the notifications and categories for the navigation
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (seller_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (seller_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

        # rendering seller page
    return render_template('seller_page.html', listings=open_listings, closed_listings=closed_listings,
                           sold_listings=sold_listings, stars=stars,
                           user_info=user_info, categories=categories, notifications=notifications,
                           unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications, logged_in=True, ratings=ratings,
                           vendor_info=vendor_info)


# page for other users to view seller
@app.route('/view_seller<seller_email>', methods=['GET', 'POST'])
def view_seller(seller_email):

    # checking session
    if 'email' not in session:
        return redirect('/login')

    # checking the user isn't visiting their own page
    user_email = session['email']
    if seller_email == user_email:
        return redirect('/seller_page')

    # connecting to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    cc.execute('SELECT * FROM sellers WHERE email = ?', (user_email,))
    seller = cc.fetchone()
    if seller:
        seller = True
    else:
        seller = False

    # getting vendor info
    cc.execute('SELECT * FROM local_vendors WHERE email = ?', (seller_email,))
    vendor_info = cc.fetchone()

    # getting user info
    cc.execute('SELECT * FROM bidders WHERE email = ?', (seller_email,))
    user_info = cc.fetchone()

    # getting ratings
    cc.execute('SELECT * FROM rating WHERE seller_email = ?', (seller_email,))
    ratings = cc.fetchall()

    # getting open listings
    cc.execute(
        'SELECT auction_title, product_name, product_description,reserve_price,listing_id FROM auction_listings WHERE seller_email = ? and status=1',
        (seller_email,))
    listings = cc.fetchall()

    # getting rating in stars
    cc.execute('SELECT AVG(rating) FROM rating WHERE seller_email = ?', (seller_email,))
    rating_avg = cc.fetchone()[0]
    stars = int(round(rating_avg)) if rating_avg is not None else 0

    # getting categories and notifications for nav
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

        # rendering seller template
    return render_template('view_seller.html', seller_email=seller_email, listings=listings, stars=stars,
                           user_info=user_info, categories=categories, notifications=notifications,
                           unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications, logged_in=True, ratings=ratings,
                           vendor_info=vendor_info, seller=seller)


# add product
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    # checking session
    if 'email' not in session:
        return redirect('/login')

    # connecting to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # getting categories
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()

    # getting session email
    user_email = session['email']

    # getting notifications for nav
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

    # getting request method
    if request.method == 'POST':
        seller_email = user_email
        listing_id = random.randint(100000, 999999)
        category = request.form['category']
        auction_title = request.form['auction_title']
        product_name = request.form['product_name']
        product_desc = request.form['product_desc']
        quantity = request.form['quantity']
        reserve_price = request.form['reserve_price']
        max_bids = request.form['max_bids']
        status = 1

        # adding new listing into auction_listings
        cc.execute(
            'INSERT INTO auction_listings (seller_email, listing_id, category, auction_title, product_name, product_description, quantity, reserve_price, max_bids, status) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (seller_email, listing_id, category, auction_title, product_name, product_desc, quantity, reserve_price,
             max_bids, status))
        conn.commit()

        # redirect to seller page
        return redirect('/seller_page')

    # render template
    return render_template('add_product.html', categories=categories, logged_in=True, seller=True,
                           notifications=notifications, unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications)


# edit prodict
@app.route('/edit_product<listing_id>', methods=['GET', 'POST'])
def edit_product(listing_id):
    # checking session
    if 'email' not in session:
        return redirect('/login')
    user_email = session['email']

    # connect to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # getting categories
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()

    # getting notifs
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

    # checking method
    if request.method == 'POST':
        seller_email = user_email
        category = request.form['category']
        auction_title = request.form['auction_title']
        product_name = request.form['product_name']
        product_desc = request.form['product_desc']
        quantity = request.form['quantity']
        reserve_price = request.form['reserve_price']
        max_bids = request.form['max_bids']
        status = request.form['status']

        # applying new values to each form if applicable
        if category and category != 'None':
            cc.execute('''UPDATE auction_listings
                          SET category = ?
                          WHERE listing_id = ?''', (category, listing_id))
            conn.commit()

        if auction_title:
            cc.execute('''UPDATE auction_listings
                          SET auction_title = ?
                          WHERE listing_id = ?''', (auction_title, listing_id))
            conn.commit()

        if product_name:
            cc.execute('''UPDATE auction_listings
                          SET product_name = ?
                          WHERE listing_id = ?''', (product_name, listing_id))
            conn.commit()

        if product_desc:
            cc.execute('''UPDATE auction_listings
                          SET product_description = ?
                          WHERE listing_id = ?''', (product_desc, listing_id))
            conn.commit()

        if quantity:
            cc.execute('''UPDATE auction_listings
                          SET quantity = ?
                          WHERE listing_id = ?''', (quantity, listing_id))
            conn.commit()

        if reserve_price:
            cc.execute('''UPDATE auction_listings
                          SET reserve_price = ?
                          WHERE listing_id = ?''', (reserve_price, listing_id))
        if max_bids:
            cc.execute('''UPDATE auction_listings
                          SET max_bids = ?
                          WHERE listing_id = ?''', (max_bids, listing_id))
            conn.commit()

        if status:
            cc.execute('''UPDATE auction_listings
                          SET status = ?
                          WHERE listing_id = ?''', (status, listing_id))
            conn.commit()

        return redirect('/seller_page')
    return render_template('edit_product.html', categories=categories, logged_in=True, seller=True,
                           notifications=notifications, unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications, listing_id=listing_id)


# delete product
@app.route('/delete_product<listing_id>', methods=['GET', 'POST'])
def delete_product(listing_id):
    # getting session
    if 'email' not in session:
        return redirect('/login')

    # connect to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # getting categories
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    user_email = session['email']

    # getting notifs
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

    # checking request
    if request.method == 'POST':
        # deleting from listing
        cc.execute(
            'DELETE FROM auction_listings WHERE listing_id = ?', (listing_id,))
        conn.commit()
        return redirect('/seller_page')

    # render template
    return render_template('delete_product.html', categories=categories, logged_in=True, seller=True,
                           notifications=notifications, unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications, listing_id=listing_id)


# reviews
@app.route('/review<seller_email>', methods=['GET', 'POST'])
def review(seller_email):
    # checking session
    if 'email' not in session:
        return redirect('/login')

    # connect to DB
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()

    # getting categories
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()

    # checking email
    user_email = session['email']

    # user cannot review their selves
    if user_email == seller_email:
        return redirect('/')

    # getting notifs
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

    # checking seller
    cc.execute('''SELECT *
                                        FROM sellers
                                        WHERE email = ?''', (user_email,))
    seller = cc.fetchone()

    # checking request
    if request.method == 'POST':

        # user cannot review unless they have purchased something
        cc.execute("SELECT * from transactions WHERE seller_email=? AND buyer_email=?", (seller_email, user_email))
        real_user_check = cc.fetchall()

        # saving user email as bidder
        bidder_email = user_email

        # getting rating and description from form
        rating = request.form['rating']
        rating_desc = request.form['rating_desc']

        # user cannot rate themselves
        if user_email == seller_email:
            return redirect('/')

        # if user has not purchased something they cannot review
        if not real_user_check:
            return render_template('review.html', error='You have not bought something from this seller yet.',
                                   categories=categories, logged_in=True)

        # making sure user has rating and desc
        if not rating:
            return render_template('review.html', error='Please add a rating.', categories=categories, logged_in=True)
        if not rating_desc:
            return render_template('review.html', error='Please add a rating description.', categories=categories,
                                   logged_in=True)

        # getting date
        current_date = datetime.datetime.now()
        current_date_str = current_date.strftime("%Y-%m-%d %H:%M:%S")

        # connect to DB
        conn = sqlite3.connect('database.db')
        cc = conn.cursor()

        # out in ratings
        cc.execute('''INSERT INTO rating (bidder_email, seller_email, date, rating, rating_desc)
                             VALUES (?, ?, ?, ?, ?)''',
                   (bidder_email, seller_email, current_date_str, rating, rating_desc))
        conn.commit()
        conn.close()

        return redirect('/')
    else:
        if 'email' in session:
            if seller:
                return render_template('review.html', logged_in=True, seller=True, categories=categories,
                                       notifications=notifications, unread_notification_count=unread_notification_count,
                                       has_unread_notifications=has_unread_notifications)
            else:
                return render_template('review.html', logged_in=True, seller=False, categories=categories,
                                       notifications=notifications, unread_notification_count=unread_notification_count,
                                       has_unread_notifications=has_unread_notifications)
        else:
            return render_template('review.html', logged_in=False, seller=False, categories=categories)


@app.route('/products/<category>')
def products(category):
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()
    cc.execute("SELECT * FROM auction_listings WHERE category=? and status=1", (category,))
    listings = cc.fetchall()
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    if 'email' in session:
        user_email = session['email']
        cc.execute('''SELECT *
                                    FROM sellers
                                    WHERE email = ?''', (user_email,))
        seller = cc.fetchone()

        cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
        notifications = cc.fetchall()
        cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
        unread_notification_count = cc.fetchone()[0]
        if unread_notification_count:
            has_unread_notifications = True
        else:
            has_unread_notifications = False
        if seller:
            return render_template('products.html', category=category, listings=listings, logged_in=True, seller=True,
                                   categories=categories, notifications=notifications,
                                   unread_notification_count=unread_notification_count,
                                   has_unread_notifications=has_unread_notifications)
        else:
            return render_template('products.html', category=category, listings=listings, logged_in=True, seller=False,
                                   categories=categories, notifications=notifications,
                                   unread_notification_count=unread_notification_count,
                                   has_unread_notifications=has_unread_notifications)
    else:
        return render_template('products.html', category=category, listings=listings, logged_in=False, seller=False,
                               categories=categories)


@app.route('/search')
def search():
    query = request.args.get('query')
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()
    cc.execute(
        "SELECT * FROM auction_listings WHERE status = 1 AND (product_name LIKE ? OR product_description LIKE ?)",
        ('%' + query + '%', '%' + query + '%'))
    listings = cc.fetchall()
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()

    if 'email' in session:
        user_email = session['email']
        cc.execute('''SELECT *
                                    FROM sellers
                                    WHERE email = ?''', (user_email,))
        seller = cc.fetchone()
        cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
        notifications = cc.fetchall()
        cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
        unread_notification_count = cc.fetchone()[0]
        if unread_notification_count:
            has_unread_notifications = True
        else:
            has_unread_notifications = False
        if seller:
            return render_template('search_results.html', query=query, listings=listings, logged_in=True, seller=True,
                                   categories=categories, notifications=notifications,
                                   unread_notification_count=unread_notification_count,
                                   has_unread_notifications=has_unread_notifications)
        else:
            return render_template('search_results.html', query=query, listings=listings, logged_in=True, seller=False,
                                   categories=categories, notifications=notifications,
                                   unread_notification_count=unread_notification_count,
                                   has_unread_notifications=has_unread_notifications)
    else:
        return render_template('search_results.html', query=query, listings=listings, logged_in=False, seller=False,
                               categories=categories)


@app.route('/notification/<notification_id>', methods=['GET', 'POST'])
def notification(notification_id):
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()
    user_email = session['email']
    cc.execute("SELECT * FROM notifications WHERE notification_id=?", (notification_id,))
    notification = cc.fetchone()
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False
    bid_id = notification[3]
    notif_type = notification[4]

    cc.execute("SELECT * from bids where bid_id =?", (bid_id,))
    bid = cc.fetchone()
    seller_email = bid[1]
    bidder_email = bid[3]
    listing_id = bid[2]
    user_bid_price = bid[4]
    cc.execute("SELECT * from auction_listings where listing_id=?", (listing_id,))
    listing = cc.fetchone()
    product_name = listing[4]
    if request.method == 'POST':
        action = request.form['action']
        if notif_type == 'reserve_CD':
            if action == 'confirm':
                new_notif_id = str(uuid.uuid4())
                cc.execute('UPDATE notifications SET notif_action =? where notification_id=?',
                           ('closed', notification_id))
                cc.execute(
                    'INSERT INTO notifications (notification_id,email,notif_title,notif_bid,notif_action,notif_type) VALUES (?,?,?,?,?,?)',
                    (new_notif_id, bidder_email, 'Bid accepted for ' + product_name + '! Please click to pay.', bid_id,
                     'unread',
                     'pay'))
                conn.commit()
                return render_template('notification.html', notification=notification, error='Thank you!')

            elif action == 'deny':
                new_notif_id = str(uuid.uuid4())
                cc.execute('UPDATE notifications SET notif_action =? where notification_id=?',
                           ('closed', notification_id))
                cc.execute(
                    'INSERT INTO notifications (notification_id,email,notif_title,notif_bid,notif_action,notif_type) VALUES (?,?,?,?,?,?)',
                    (new_notif_id, bidder_email, 'Bid denied for ' + product_name + '!', bid_id,
                     'unread',
                     'denied_bid'))
                conn.commit()

                return render_template('notification.html', notification=notification, error='Thank you!')
        elif notif_type == 'bid_accept' or notif_type == 'bid_deny' or notif_type == 'bid_pending' or notif_type == 'bought' or notif_type == 'sold':
            if action == 'okay':
                cc.execute('UPDATE notifications SET notif_action =? where notification_id=?',
                           ('closed', notification_id))
                conn.commit()
                return render_template('notification.html', notification=notification, error='Thank you!')
        elif notif_type == 'pay':
            cc.execute('UPDATE notifications SET notif_action =? where notification_id=?', ('closed', notification_id))
            conn.commit()
            return redirect(url_for('payment', listing_id=listing_id, bid_id=bid_id, user_email=bidder_email,
                                    seller_email=seller_email, user_bid_price=user_bid_price, product=product_name))
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    return render_template('notification.html', notification=notification, error=None, categories=categories,
                           notifications=notifications, unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications)


@app.route('/helpdesk', methods=['GET', 'POST'])
def helpdesk():
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()
    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    if 'email' in session:
        user_email = session['email']
        conn = sqlite3.connect('database.db')
        cc = conn.cursor()
        cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
        notifications = cc.fetchall()
        cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
        unread_notification_count = cc.fetchone()[0]
        if unread_notification_count:
            has_unread_notifications = True
        else:
            has_unread_notifications = False
        cc.execute('''SELECT *
                                        FROM sellers
                                        WHERE email = ?''', (user_email,))
        seller = cc.fetchone()
    if request.method == 'POST':
        if 'email' in session:
            sender_email = session['email']
        else:
            sender_email = request.form['sender_email']
        request_type = request.form['request_type']
        request_desc = request.form['request_desc']
        request_status = '0'

        if not request_type:
            return render_template('helpdesk.html', error='Please add a request type.', categories=categories)
        if not request_desc:
            return render_template('helpdesk.html', error='Please add a request description.', categories=categories)
        if not sender_email:
            return render_template('helpdesk.html', error='Please login or fill in your email. ', categories=categories)

        conn = sqlite3.connect('database.db')
        cc = conn.cursor()
        cc.execute('''INSERT INTO requests (sender_email, helpdesk_staff_email, request_type, request_desc, request_status)
                         VALUES (?, ?, ?, ?, ?)''',
                   (sender_email, 'helpdeskteam@lsu.edu', request_type, request_desc, request_status))
        conn.commit()
        conn.close()

        return redirect('/')
    else:
        if 'email' in session:
            if seller:
                return render_template('helpdesk.html', logged_in=True, seller=True, categories=categories,
                                       notifications=notifications, unread_notification_count=unread_notification_count,
                                       has_unread_notifications=has_unread_notifications)
            else:
                return render_template('helpdesk.html', logged_in=True, seller=False, categories=categories,
                                       notifications=notifications, unread_notification_count=unread_notification_count,
                                       has_unread_notifications=has_unread_notifications)
        else:
            return render_template('helpdesk.html', logged_in=False, seller=False, categories=categories)


@app.route('/product/<listing_id>', methods=['GET', 'POST'])
def product_profile(listing_id):
    if 'email' not in session:
        return redirect('/login')
    user_email = session['email']
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

    cc.execute("SELECT category_name FROM categories")
    categories = cc.fetchall()
    cc.execute("SELECT * FROM auction_listings WHERE listing_id = ?", (listing_id,))
    product_info = cc.fetchone()
    cc.execute("SELECT COUNT(*) FROM bids WHERE listing_id = ?", (listing_id,))
    num_bids = cc.fetchone()[0]
    cc.execute("SELECT MAX(bid_price) FROM bids WHERE listing_id = ?", (listing_id,))
    max_bid = cc.fetchone()[0]
    cc.execute("SELECT bidder_email FROM bids WHERE listing_id = ? ORDER BY bid_price DESC LIMIT 1", (listing_id,))
    last_bidder = cc.fetchone()
    if not max_bid:
        max_bid = 0
    if num_bids == product_info[8]:
        bid_open = False
    else:
        bid_open = True
    if request.method == 'POST':
        user_bid_price = float(request.form['user_bid_price'])
        if user_email == product_info[0]:
            return render_template('product_profile.html', logged_in=True, error='Cannot bid on your own product!',
                                   product=product_info, num_bids=num_bids, max_bid=max_bid, bid_open=bid_open)
        if user_bid_price <= 0:
            return render_template('product_profile.html', logged_in=True, error='Not a valid bid!',
                                   product=product_info, num_bids=num_bids, max_bid=max_bid, bid_open=bid_open)
        elif user_bid_price < max_bid + 1:
            return render_template('product_profile.html', logged_in=True, error='Must have a higher bid than last!',
                                   product=product_info, num_bids=num_bids, max_bid=max_bid, bid_open=bid_open)
        if last_bidder is not None and last_bidder[0] == user_email:
            return render_template('product_profile.html', logged_in=True,
                                   error='You must wait until another bidder submits a bid!',
                                   product=product_info, num_bids=num_bids, max_bid=max_bid, bid_open=bid_open)
        bid_id = str(uuid.uuid4())
        seller_email = product_info[0]
        cc.execute('INSERT INTO bids (bid_id, seller_email, listing_id, bidder_email, bid_price) VALUES (?,?,?,?,?)',
                   (bid_id, seller_email, listing_id, user_email, user_bid_price))
        cc.execute("SELECT COUNT(*) FROM bids WHERE listing_id = ?", (listing_id,))
        num_bids = cc.fetchone()[0]
        cc.execute("SELECT MAX(bid_price) FROM bids WHERE listing_id = ?", (listing_id,))
        max_bid = cc.fetchone()[0]
        conn.commit()
        # Insignia? - 65" Class F30 Series LED 4K UHD Smart Fire TV
        if num_bids == product_info[8]:
            if user_bid_price < product_info[7]:
                bid_open = False
                cc.execute('UPDATE auction_listings SET quantity =? where listing_id=?',
                           ((product_info[6] - 1), listing_id))
                cc.execute('UPDATE auction_listings SET status =? where listing_id=?', ('2', listing_id))
                notif_id = str(uuid.uuid4())
                cc.execute(
                    'INSERT INTO notifications (notification_id,email,notif_title,notif_bid,notif_action, notif_type) VALUES (?,?,?,?,?,?)',
                    (notif_id, seller_email, 'Confirm or deny this bid', bid_id, 'unread', 'reserve_CD'))

                cc.execute('SELECT bidder_email FROM bids WHERE listing_id=?', (listing_id,))
                email_other_bidders = cc.fetchall()
                bidder_check = []
                for bidder_email in email_other_bidders:
                    print(bidder_email)
                    notif_id = str(uuid.uuid4())
                    if bidder_email[0] not in bidder_check:
                        cc.execute(
                            'INSERT INTO notifications (notification_id,email,notif_title,notif_bid,notif_action, notif_type) VALUES (?,?,?,?,?,?)',
                            (notif_id, bidder_email[0],
                             'Final bidder did not exceed reserve price. Please wait for more information.', bid_id,
                             'unread', 'bid_pending'))
                        bidder_check.append(bidder_email[0])
                conn.commit()
                return render_template('product_profile.html', logged_in=True,
                                       error='Final bid not higher than reserve price. Seller will notify you if the item is sold to you.',
                                       product=product_info,
                                       num_bids=num_bids, max_bid=max_bid, bid_open=bid_open)

            bid_open = False
            cc.execute('UPDATE auction_listings SET quantity =? where listing_id=?', (product_info[6] - 1, listing_id))
            cc.execute('UPDATE auction_listings SET status =? where listing_id=?', ('2', listing_id))
            cc.execute('SELECT bidder_email FROM bids WHERE listing_id=?', (listing_id,))
            email_other_bidders = cc.fetchall()
            bidder_check = []
            for bidder_email in email_other_bidders:
                notif_id = str(uuid.uuid4())
                if bidder_email[0] == user_email:
                    cc.execute(
                        'INSERT INTO notifications (notification_id,email,notif_title,notif_bid,notif_action,notif_type) VALUES (?,?,?,?,?,?)',
                        (notif_id, bidder_email[0], 'Bid accepted for ' + product_info[3] + '!', bid_id, 'unread',
                         'bid_accept'))
                else:
                    if bidder_email[0] not in bidder_check:
                        cc.execute(
                            'INSERT INTO notifications (notification_id,email,notif_title,notif_bid,notif_action,notif_type) VALUES (?,?,?,?,?,?)',
                            (notif_id, bidder_email[0], 'Bid denied for ' + product_info[3] + '! Try again next time!',
                             bid_id, 'unread', 'bid_deny'))
                        bidder_check.append(bidder_email[0])
            conn.commit()
            return redirect(url_for('payment', listing_id=listing_id, bid_id=bid_id, user_email=user_email,
                                    seller_email=seller_email, user_bid_price=user_bid_price, product=product_info[3]))
    return render_template('product_profile.html', logged_in=True, error=None,
                           product=product_info, num_bids=num_bids, max_bid=max_bid, bid_open=bid_open,
                           notifications=notifications, unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications, categories=categories)


@app.route('/payment', methods=['POST', 'GET'])
def payment():
    conn = sqlite3.connect('database.db')
    cc = conn.cursor()
    bid_id = request.args.get('bid_id')
    listing_id = request.args.get('listing_id')
    user_email = request.args.get('user_email')
    seller_email = request.args.get('seller_email')
    user_bid_price = request.args.get('user_bid_price')
    product = request.args.get('product')
    print(product)
    print(user_bid_price)
    cc.execute(
        "SELECT credit_card_num, card_type, expire_month, expire_year, security_code FROM credit_cards WHERE owner_email=?",
        (user_email,))
    cards = cc.fetchall()
    user_email = session['email']
    cc.execute("SELECT * FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    notifications = cc.fetchall()
    cc.execute("SELECT COUNT(*) FROM notifications WHERE email =? and notif_action !=?", (user_email, 'closed'))
    unread_notification_count = cc.fetchone()[0]
    if unread_notification_count:
        has_unread_notifications = True
    else:
        has_unread_notifications = False

    if request.method == 'POST':
        # Get the form data from the request
        card_num = request.form['card_num']
        card_type = request.form['card_type']
        expire_month = request.form['expire_month']
        expire_year = request.form['expire_year']
        security_code = request.form['security_code']
        action = request.form['action']
        bid_id = request.form['bid_id']
        listing_id = request.form['listing_id']
        user_email = request.form['user_email']
        seller_email = request.form['seller_email']
        user_bid_price = request.form['user_bid_price']
        product = request.form['product']
        print(product)
        print(user_bid_price)
        # Perform the appropriate action based on the form data
        if action == 'add':
            # Add a new credit card to the database
            cc.execute(
                "INSERT INTO credit_cards (credit_card_num, card_type, expire_month, expire_year, security_code, owner_email) VALUES (?, ?, ?, ?, ?, ?)",
                (card_num, card_type, expire_month, expire_year, security_code, email))
            transaction_id = str(uuid.uuid4())
            current_date = datetime.datetime.now()
            current_date_str = current_date.strftime("%Y-%m-%d %H:%M:%S")
            cc.execute(
                "INSERT INTO transactions (transaction_id, seller_email, listing_id, buyer_email, date, payment) VALUES (?, ?, ?, ?, ?, ?)",
                (transaction_id, seller_email, listing_id, user_email, current_date_str, card_num))
            cc.execute('SELECT balance FROM sellers where seller_email=?', (seller_email,))
            last_balance = cc.fetchone()
            cc.execute('UPDATE sellers SET balance =? where email=?', (last_balance + user_bid_price, seller_email))

            notification_id = str(uuid.uuid4())
            cc.execute(
                "INSERT INTO notifications (notification_id, email, notif_title, notif_bid, notif_action, notif_type) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    notification_id, seller_email, 'Your item ' + product + ' has sold for $' + str(user_bid_price),
                    bid_id,
                    'unread', 'sold'))
            notification_id = str(uuid.uuid4())
            cc.execute(
                "INSERT INTO notifications (notification_id, email, notif_title, notif_bid, notif_action, notif_type) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    notification_id, user_email, 'You bought ' + product + ' for $' + str(user_bid_price),
                    bid_id,
                    'unread', 'bought'))
            conn.commit()

            return render_template('profile.html')
        elif action == 'card_list_item':
            transaction_id = str(uuid.uuid4())
            current_date = datetime.datetime.now()
            current_date_str = current_date.strftime("%Y-%m-%d %H:%M:%S")
            cc.execute(
                "INSERT INTO transactions (transaction_id, seller_email, listing_id, buyer_email, date, payment) VALUES (?, ?, ?, ?, ?, ?)",
                (transaction_id, seller_email, listing_id, user_email, current_date_str, user_bid_price))
            notification_id = str(uuid.uuid4())
            cc.execute(
                "INSERT INTO notifications (notification_id, email, notif_title, notif_bid, notif_action, notif_type) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    notification_id, seller_email, 'Your item ' + product + ' has sold for $' + str(user_bid_price),
                    bid_id,
                    'unread', 'sold'))
            notification_id = str(uuid.uuid4())
            cc.execute(
                "INSERT INTO notifications (notification_id, email, notif_title, notif_bid, notif_action, notif_type) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    notification_id, user_email, 'You bought ' + product + ' for $' + str(user_bid_price),
                    bid_id,
                    'unread', 'bought'))
            conn.commit()

            cc.execute('''SELECT b.first_name, b.last_name, b.email, b.gender, b.age, a.street_num, a.street_name, z.city, z.state, a.zipcode, b.major
                                     FROM bidders b JOIN address a ON b.home_address_id = a.address_id JOIN zipcode_info z ON a.zipcode = z.zipcode
                                     WHERE b.email = ?''', (user_email,))
            user_info = cc.fetchone()
            cc.execute('''SELECT email, bank_num, bank_account, balance FROM sellers WHERE email = ?''', (user_email,))
            seller_info = cc.fetchone()
            cc.execute("SELECT category_name FROM categories")
            categories = cc.fetchall()
            if seller_info:
                return render_template('profile.html', user_info=user_info, seller_info=seller_info, seller=True,
                                       categories=categories)
            # render profile template with user's information
            else:
                return render_template('profile.html', user_info=user_info, seller=False, categories=categories)

    return render_template('payment.html', bid_id=bid_id, user_email=user_email,
                           seller_email=seller_email, user_bid_price=user_bid_price, product=product, cards=cards,
                           notifications=notifications, unread_notification_count=unread_notification_count,
                           has_unread_notifications=has_unread_notifications)


# logging out the user
@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
