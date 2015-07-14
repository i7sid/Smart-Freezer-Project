import os
import glob
import base64
import json
import sys

from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, _app_ctx_stack
from datetime import datetime, timedelta
from collections import OrderedDict

from epex import parse_epex
from pca301 import parse_pca301

sys.path.append( '../../fingerprint' )
from FingerprintServiceClient import FingerprintServiceClient

# configuration
DATABASE = os.path.dirname(os.path.realpath(__file__)) + '/database.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

fpserv = FingerprintServiceClient()

def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        sqlite_db = sqlite3.connect(app.config['DATABASE'])
        sqlite_db.row_factory = sqlite3.Row
        top.sqlite_db = sqlite_db

    return top.sqlite_db


@app.teardown_appcontext
def close_db_connection(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()

#db = get_db()
#cur = db.execute('select title, text from entries order by id desc')
#entries = cur.fetchall()

@app.route('/', methods=['GET', 'POST'])
def temperature():
    temp_graph1 = None
    temp_graph2 = None
    if os.path.isfile("/var/www/temp_graph.png"):
        temp_graph1 = base64.b64encode(open("/var/www/temp_graph.png").read())
        temp_graph2 = base64.b64encode(open("/var/www/temp_graph2.png").read())

    temp_set = None
    if os.path.isfile("/run/shm/temp.set"):
        temp_set = open("/run/shm/temp.set").read()

    if request.method == 'POST':
        open("/run/shm/temp.wish", "w").write(request.form['ctrlTemp'])

    return render_template('index.html', active=1, temp_graph1=temp_graph1, temp_graph2=temp_graph2, temp_set=temp_set)

@app.route("/status")
def status():
    relais, temp_inside, temp_outside = '', '', ''

    if os.path.isfile("/run/shm/relais.status"):
        relais = open("/run/shm/relais.status").read()
        temp_inside = open("/run/shm/temp.inside").read()
        temp_outside = open("/run/shm/temp.outside").read()

    return json.dumps({'temp_inside': temp_inside, 'temp_outside': temp_outside, 'relais': relais})

@app.route("/webcam")
def webcam():
    files = glob.glob("/data/pictures/image-*.jpg")
    images = []
    for file in files:
        images.append(base64.b64encode(open(file).read()))

    return render_template('webcam.html', active=3, images=images)

@app.route("/accounting", methods=['GET', 'POST'])
def accounting():
    if request.method == 'POST':
        fpserv.add_user(request.form['name'])
        flash('Benutzer wurde angelegt')
        return redirect(url_for('accounting'))

    return render_template('accounting.html', active=4, users=fpserv.get_users(), state=fpserv.get_state())

@app.route("/remove_user/<int:user_id>", methods=['GET', 'POST'])
def remove_user(user_id):
    user = fpserv.get_user(user_id)
    fpserv.remove_user(user['id'])
    flash('Benutzer wurde geloescht')
    return redirect(url_for('accounting'))

@app.route("/remove_fingerprint/<int:fingerprint_id>", methods=['GET', 'POST'])
def remove_fingerprint(fingerprint_id):
    fpserv.remove_fingerprint(fingerprint_id)
    flash('Fingerabdruck wurde geloescht')
    return redirect(url_for('accounting'))

@app.route("/enroll/<int:user_id>", methods=['GET', 'POST'])
def enroll(user_id):
    user = fpserv.get_user(user_id)
    fpserv.enroll(user['id'])
    flash('Finerabdruckspeicherung wurde gestartet...')
    return redirect(url_for('accounting'))

@app.route("/bookings/<int:user_id>", methods=['GET', 'POST'])
def bookings(user_id):
    user = fpserv.get_user(user_id)
    if request.method == 'POST':
        fpserv.add_booking(user['id'], request.form['count'])
        flash('Ausgleichsbuchung wurde hinzugefuegt')
        return redirect(url_for('bookings', user_id=user['id']))

    return render_template('bookings.html', active=4, user=user, bookings=fpserv.get_bookings(user['id']))

@app.route("/edit_user/<int:user_id>", methods=['GET', 'POST'])
def edit_user(user_id):
    user = fpserv.get_user(user_id)
    if request.method == 'POST':
        user['name'] = request.form['name']
        fpserv.change_user(user)
        flash('Benutzer wurde bearbeitet')
        return redirect(url_for('accounting'))

    return render_template('edit_user.html', active=4, user=user)

@app.route('/energy')
def energy():
    updatePca301()
    date = datetime.now() - timedelta(days=30)
    daysString = []
    daysCons = []
    while date < datetime.now():
        daysCons.append(get_energy_consumption(date.strftime("%Y-%m-%d")))
        daysString.append(date.strftime("%d. %b"))
        date += timedelta(days=1)

    res = {}

    date = datetime.now() - timedelta(days=5)
    date2 = datetime.now() + timedelta(days=1)

    total = {}

    while (date < date2):
        day = date.strftime("%d. %b")

        res[day] = {}

        cost_total_epex = 0
        cost_total_std = 0

        for hour in range(0, 24):
            cost_epex = None
            kwh_epex = get_epex_price(date.strftime("%Y-%m-%d"), hour)
            if kwh_epex is not None:
                cost_epex = ( get_energy_consumption(date.strftime("%Y-%m-%d"), hour) / 1000 ) * kwh_epex
                cost_total_epex += cost_epex

            cost_total_std += ( get_energy_consumption(date.strftime("%Y-%m-%d"), hour) / 1000 ) * 26.50

            if cost_epex is not None:
                cost_epex = round(cost_epex, 2)

            res[day][hour] = {
                'consumption': get_energy_consumption(date.strftime("%Y-%m-%d"), hour),
                'kwh_epex': get_epex_price(date.strftime("%Y-%m-%d"), hour),
                'kwh_std': 26.50,
                'cost_epex': cost_epex,
                'cost_std': round(( get_energy_consumption(date.strftime("%Y-%m-%d"), hour) / 1000 ) * 26.50, 2),
                'temp_set': get_set_temperature(date.strftime("%Y-%m-%d"), hour)
            }

        total[date.strftime("%Y-%m-%d")] = {'epex': cost_total_epex, 'std': cost_total_std}

        date += timedelta(days=1)

    return render_template('energy.html', active=2, total=total, days=daysString, cons=daysCons, res=OrderedDict(sorted(res.items(), key=lambda t: t[0])))

@app.route('/update_epex')
def updateEpex():
    db = get_db()

    prices = parse_epex()
    for day in prices:
        for hour in prices[day]:
            c = db.execute('select id from epex_prices where day=? and hour=?', [day, hour])
            res = c.fetchone()
            if res is None:
                db.execute('insert into epex_prices (day, hour, price) values (?, ?, ?)', [day, hour, prices[day][hour]])
            else:
                db.execute('update epex_prices set price=? where id=?', [prices[day][hour], res[0]])

    db.commit()
    return ''

@app.route('/update_pca301')
def updatePca301():
    db = get_db()

    consumption = parse_pca301()

    for day in consumption:
        for hour in consumption[day]:
            #print "hour: " + str(hour) + ", day: " + str(day) + ", amount: " + str(consumption[day][hour]["total"])
            c = db.execute('select id from power_consumption where day=? and hour=?', [day, hour])
            res = c.fetchone()
            if res is None:
                db.execute('insert into power_consumption (day, hour, amount) values (?, ?, ?)', [day, hour, consumption[day][hour]["total"]])
            else:
                db.execute('update power_consumption set amount=? where id=?', [consumption[day][hour]["total"], res[0]])

    db.commit()
    return ''

@app.route('/set_set_temperature')
def set_set_temperature():
    temp = get_set_temperature(datetime.now().strftime("%Y-%m-%d"), datetime.now().hour)
    return str(temp)

def get_energy_consumption(day, hour = -1):
    db = get_db()
    if hour == -1:
        c = db.execute('select sum(amount) from power_consumption where day=?', [day])
    else:
        c = db.execute('select amount from power_consumption where day=? and hour=?', [day, hour])
    res = c.fetchone()
    if res is None or res[0] is None:
        return 0.0
    return res[0]

def get_set_temperature(day, hour):
    price = get_epex_price(day, hour)
    if price >= 26.50 or price is None:
        return -18

    calc_temp = round_temperature(-18 - 2 * (26.50 - price))
    if calc_temp > -29:
        return calc_temp
    return -29

def round_temperature(temp):
    return round(temp * 2) / 2

def get_epex_price(day, hour):
    db = get_db()
    c = db.execute('select price from epex_prices where day=? and hour=?', [day, hour])
    res = c.fetchone()
    if res is None:
        return None
    return res[0]

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

if __name__ == '__main__':
    #init_db()
    app.run(host="0.0.0.0")

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
