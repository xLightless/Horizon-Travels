from flask import Blueprint, render_template, session, redirect, url_for, request
from datetime import datetime

from website import sitemap
from website.database import Database
from website.booking_logic import Booking, preprocessor, Cancellations, preprocessor2

views = Blueprint('views', __name__)
database = Database(database="ht_database", user="root", password="Password1")

# booking_data = {} # used to store search_results data from a route

@views.route('/')
def index():
    """ Renders the index template and its search filter options """
    # print(session)
    search_items = database.get_table_column('locations', 'location')[1]
    search_filter_items = []
    for item in search_items:
        search_item = str(item).replace('(', '').replace(')', '').replace(',','').replace("'", '')
        search_filter_items.append(search_item)
    
    return render_template(
        'index.html',
        search_items = search_filter_items
    )

@views.route('/', methods=['POST', 'GET'])
def form_index_search():
    """ Gets input queries from index booking form to use for other functionality """
    
    if request.method == 'POST':
    
        radio_return        = request.form.get('params-traveller-return'),
        radio_oneway        = request.form.get('params-traveller-oneway'),
        location_from       = request.form.get('input-box-from'),
        location_to         = request.form.get('input-box-to'),
        passengers_amount   = request.form.get('passengers-amount'),
        seat_class_type     = request.form.get('seat-class-type'),
        date_from           = request.form.get('swing-from-datepicker'),
        date_to             = request.form.get('swing-to-datepicker')
        
        return_trip = str(radio_return).replace(',','').replace('(','').replace(')','').replace("'", '')
        oneway_trip = str(radio_oneway).replace(',','').replace('(','').replace(')','').replace("'", '')            
        
        # global search_results
        search_results = {}
        if location_from is not None: search_results['location_from'] = location_from
        if location_to is not None: search_results['location_to'] = location_to
        if passengers_amount is not None: search_results['passengers_amount'] = passengers_amount
        if seat_class_type is not None: search_results['seat_class_type'] = seat_class_type
        if date_from is not None: search_results['date_from'] = date_from
        # if date_to is not None: search_results['date_to'] = date_to
        search_results['date_to'] = date_to
        
        # Format search results to match comparisons
        for k,v in search_results.items():
            val = str(v).replace('(', '').replace(')', '').replace(',','').replace("'", '')
            search_results[k] = val
            
            # If any value from search results is invalid or empty then cancel booking confirmation
            if (k != 'date_to') and (search_results.get(k) == ""):
                return redirect(url_for('views.index'))

        # If not logged in then login before creating a search
        if (session.get("logged_in") is None) or (session['logged_in'] == False):
            return redirect(url_for('auth.login'))

        if (session.get("logged_in") is not None) and (session['logged_in'] == True):
            for i in range(database.count_table_rows('journey')):
                table_record = database.get_table_record('journey', i)
                
                if (search_results['location_from'] == table_record[1]) and (search_results['location_to'] == table_record[3]):
                    
                    
                    print(f"Route found for: {table_record[1]} to {table_record[3]}")
                    booking = Booking(search_results)
                    
                    # If return date is none then it must be a one way ticket or same day return
                    if search_results.get('date_to') == '':
                        search_results['date_to'] = search_results.get('date_from')
                        
                    
                    search_results['departure_time'] = table_record[2]
                    search_results['return_time'] = table_record[4]
                    contact_id = database.get_table_value_record('contacts', 'email_address', str(session['email']))[0]
                    search_results['currency_type'] = database.get_table_value_record('accounts', 'contact_id', str(contact_id))[5] # Get the database user preferred currency
                    booking = Booking(search_results)
                    
                    if (return_trip == 'on') and (oneway_trip == 'None'):
                        search_results['trip_type'] = 'Return Trip'
                        booking.return_trip = True
                    elif (return_trip == 'None') and (oneway_trip == 'on'):
                        search_results['trip_type'] = 'Oneway Trip'
                        booking.return_trip = False
                        
                    # # If conditions are met then add data into the booking object
                    # booking = Booking(search_results)
                    
                    # Apply discount and price to the UI
                    search_results['discount'] = booking.get_booking_discount()
                    # search_results['total_cost'] = booking.get_price()
                    search_results['total_cost'] = booking.get_price_string(str(search_results.get('currency_type'))) # Set total cost to price * currency
                    
                    # discount = search_results['discount']
                    # total_cost = search_results['total_cost']
                    
                    preprocessor.set_dict(search_results)
                    
                    return render_template('search.html', search_items = search_results)
                
                # If search does not match then cancel search
                if (i == database.count_table_rows('journey')) and (search_results['location_from'] != table_record[1]) and (search_results['location_to'] != table_record[3]):
                    return redirect(url_for('views.index'))
                
        return redirect(url_for('views.index'))

@views.route('/about-us/')
def about():
    # print()
    return render_template('about.html')

@views.route('/terms-and-conditions/')
def legal():
    return render_template('legal.html')

@views.route('/account/')
def account_page():
    """ Redirects the user from auth to the genuine account page """
    if session['logged_in'] == False:
        return redirect(url_for('auth.login'))
    
    contacts = database.get_table_value_record('contacts', 'email_address', str(session['email']))
    contact_id = contacts[0]
    customer_id = contacts[1]
    telephone = contacts[2]
    email = contacts[3]
    
    customer = database.get_table_value_record('customers', 'customer_id', str(customer_id))
    fname = customer[1]
    lname = customer[2]
    
    accounts = database.get_table_value_record('accounts', 'contact_id', str(contact_id))
    username = accounts[2]
    
    account_id = accounts[0]
    
    # 1. SEARCH THROUGH ACCOUNT IDS FOR ALL BOOKINGS AND DYNAMICALLY UPDATE TO TABLE IN DASHBOARD
    data = database.get_table_records_of_key('booking_payment', 'account_id', account_id)
    # print(data)
    
    # Get the row column value using list length rather than absolute value
    booking_data = {}
    cancellation_data = {}
    currency_type = str(accounts[5])
    
    
    # Set a cancellation-date in database when cancellation has been created so that is no bug    

    # cancellation_date = str(datetime.now().date()).replace('-','/') # Date of cancellation
    
    for row in range(len(data)):
        
        journey_record = database.get_table_value_record('journey', 'journey_id', str(data[row][7]))
        location_from = str(journey_record[1])
        location_to =  str(journey_record[3])
        price           = data[row][2]
        payment_method  = data[row][4]
        payment_date    = data[row][5]
        purchase_status = data[row][6]
    
    
    
        booking_table = database.get_table_value_record('booking', 'payment_id', str(data[row][0]))
        
        if str(purchase_status) == 'Approved':
        
            booking_data[row] = {
                'location_from'     :   location_from,
                'location_to'       :   location_to,
                'commute_type'      :   booking_table[6],
                'price'             :   price,
                'payment_method'    :   payment_method,
                'payment_date'      :   payment_date,
                'purchase_status'   :   purchase_status,
            }
            
            user_table_data = Booking(booking_data)
            
            # Update the current price to the exchanged price before displaying to the page
            price = float(booking_data[row]['price'])
            exchanged_price = user_table_data.interate_price_string(price, currency_type)
            booking_data[row]['price'] = exchanged_price
            
            # Sets payment_id of each row
            booking_data[row]['payment_id'] = booking_table[1]
           
            # Delete bad booking data that was not removed in the UI
            if booking_data[row]['payment_id'] == 'n':
                booking_data.pop(row)
        
        elif str(purchase_status) == 'Cancelled':
            if data[row][8] is None:
                continue
            else:
                cancellation_date = data[row][8]
            
            # print(type(data[row][8]))
            # Go to next iteration if cancellation_date is NULL
            # if (type(data[row][8]) != datetime.date):
            #     print(True)
            # cancellation_date = data[row][8] if data[row][8] is not None else ''
            # else:
            #     continue
            
            booking_date = str(booking_table[4]).replace('-', '/')
            cancellation = Cancellations(float(price), currency_type, cancellation_date, booking_date)
            cancel_fee = cancellation.get_cancellation_fee()
            
            cancellation_data[row] = {
                'payment_id'        :   data[row][0],
                'purchase_status'   :   purchase_status,
                'booking_date'      :   booking_table[4]
            }
            
            cancellation_data[row]['cancellation_date'] = cancellation_date
            
            # Convert the price and cancellation fee
            if (currency_type == 'Euros'):
                currency_type_symbol = '€'
                cancellation_data[row]['price'] = "%s" % (cancellation.get_price_string())
                cancellation_data[row]['cancellation_fee'] = "%s%.2f" % (currency_type_symbol, cancel_fee * 1.13)
            
            elif (currency_type == 'Dollars'):
                currency_type_symbol = '$'
                cancellation_data[row]['price'] = "%s" % (cancellation.get_price_string())
                cancellation_data[row]['cancellation_fee'] = "%s%.2f" % (currency_type_symbol, cancel_fee * 1.25)
            
            else:
                currency_type_symbol = '£'
                cancellation_data[row]['price'] = "%s" % (cancellation.get_price_string())
                cancellation_data[row]['cancellation_fee'] = "%s%.2f" % (currency_type_symbol, cancel_fee * 1)
        
        # cancellation_data[row]['cancellation_date'] = cancellation_date
        
        

    # 2. DELETE OLD RECORDS FROM DATABASE IF RETURN_DATE HAS BEEN SURPASSED
        
    
    
    return render_template(
        'account.html',
        current_username = str(username),
        current_fname = str(fname),
        current_lname = str(lname),
        current_telephone = str(telephone),
        current_email = str(email),
        booking_data = booking_data,
        currency_type = str(accounts[5]),
        cancellation_data = cancellation_data
        )

@views.route('/account/<username>/<fname>/<lname>/<telephone>/<email>/')
def update_account(username, fname, lname, telephone, email):
    return redirect(url_for('auth.account'))

@sitemap.register_generator
def pages():
    yield 'views.index', {}, datetime.now(), 'monthly', 0.7
    # yield 'views.booking', {}, datetime.now(), 'monthly', 0.7
    yield 'views.about', {}, datetime.now(), 'monthly', 0.7
    yield 'views.legal', {}, datetime.now(), 'monthly', 0.7