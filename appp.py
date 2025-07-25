from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from flask import Flask, request, jsonify
from celery import Celery
from flask_session import Session
from datetime import datetime, date,timedelta
from flask_mail import Mail, Message
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
import MySQLdb.cursors
import google.generativeai as genai
import os
import sys
from celery.schedules import crontab
import redis
import json

#python file

app = Flask(__name__)




app.secret_key = 'abc3445'  
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'influ'


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587 
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False  
app.config['MAIL_USERNAME'] = 'msahithreddy5@gmail.com'
app.config['MAIL_PASSWORD'] = 'bjzw hlkn rjih ifjb'
app.config['MAIL_DEFAULT_SENDER'] = 'msahithreddy5@gmail.com'
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False


app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

mysql = MySQL(app)




app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'session:'
app.config['SESSION_REDIS'] = redis.StrictRedis(host='localhost', port=6379, db=0)


Session(app)
mail = Mail(app)

cache = redis.StrictRedis(host='localhost', port=6379, db=1)
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['CELERY_RESULT_BACKEND'])


GOOGLE_CHAT_WEBHOOK_URL = 'https://mail.google.com/chat/u/0/#chat/space/AAAA3MvjGyM'

celery.conf.beat_schedule.update({
    'send-daily-reminders': {
        'task': 'send_daily_reminders',
        'schedule': crontab(hour=18, minute=0),  
    },
})
genai.configure(api_key="AIzaSyCuRIopGxIzAVTG-j-Ag2A4VwXHhSOKURY")



@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json() or {}
    user_msg = data.get('message', '').strip()
    if not user_msg:
        return jsonify(response="Please type something!"), 400

    try:
        # Define the pre-prompt for influencer sponsorship context
        system_prompt = (
            "You are an assistant specialized in helping influencers understand and manage sponsorships. "
            "Provide advice on finding brand deals, negotiating contracts, setting pricing, and building a media kit. "
            "Answer all questions from the perspective of influencer marketing and sponsorships."
        )

        # Create the chat model and start chat with system prompt
        model = genai.GenerativeModel('gemini-1.5-flash')
        chat = model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]}
        ])

        # Send the user’s message
        response = chat.send_message(user_msg)
        bot_reply = response.text

        return jsonify(response=bot_reply)

    except Exception as e:
        return jsonify(response=f"Error: {str(e)}"), 500


def date_handler(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def get_cached_data(key):
    data = cache.get(key)
    if data:
        return json.loads(data)
    return None

def set_cache_data(key, data, expiration=3600):
    json_data = json.dumps(data, default=date_handler)
    cache.set(key, json_data, ex=expiration)

def parse_dates(data):
    for item in data:
        if 'sdate' in item and isinstance(item['sdate'], str):
            item['sdate'] = datetime.strptime(item['sdate'], '%Y-%m-%d').date()
        if 'date' in item and isinstance(item['date'], str):
            item['date'] = datetime.strptime(item['date'], '%Y-%m-%d').date()
    return data




def is_last_day_of_month():
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    return today.month != tomorrow.month

@celery.task
def send_monthly_report_task(email):
    if is_last_day_of_month():
        send_monthly_report(email)


celery.conf.beat_schedule = {
    'check-and-send-monthly-report': {
        'task': 'send_monthly_report_task',
        'schedule': crontab(hour=23, minute=59),  
        'args': ('msahithreddy123@gmail.com',) 
    },
}

def send_monthly_report(email):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM campaign WHERE MONTH(date) = MONTH(CURDATE()) AND YEAR(date) = YEAR(CURDATE())')
    campaigns = cursor.fetchall()
    cursor.close()
    msg = Message('Monthly Report', recipients=[email])
    msg.body = 'Monthly_report'
    msg.html = render_template('monthly_report.html', campaigns=campaigns)
    mail.send(msg)

@celery.task
def send_daily_reminders():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT username, email 
        FROM login 
        WHERE category = 'Influencer' AND (/* Add your logic to check pending ad requests or last visit */)
    ''')
    influencers = cursor.fetchall()
    for influencer in influencers:
        username = influencer['username']
        email = influencer['email']
        send_google_chat_reminder(username)
        send_email_reminder(email, username)
    cursor.close()

def send_google_chat_reminder(username):
    message = {
        'text': f'Hi {username}, you have pending ad requests. Please visit the platform to accept them or check out public ad requests.'
    }
    response = request.post(GOOGLE_CHAT_WEBHOOK_URL, json=message)
    if response.status_code != 200:
        print(f'Failed to send Google Chat message: {response.status_code}, {response.text}')

def send_email_reminder(email, username):
    msg = Message('Daily Reminder', recipients=[email])
    msg.body = f'Hi {username}, you have pending ad requests. Please visit the platform to accept them or check out public ad requests.'
    mail.send(msg)




@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        
        cache_key = f'user_{username}'
        user = get_cached_data(cache_key)

        if not user:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM login WHERE username = %s AND password = %s', (username, password,))
            user = cursor.fetchone()
            if user:
                set_cache_data(cache_key, user)

        if user:
            session['loggedin'] = True
            session['username'] = user['username']
            session['value'] = user['value']
            if user['category'] == 'Influencer':
                return redirect(url_for('dash'))
            elif user['category'] == 'sponser':
                return redirect(url_for('dash1'))
            else:
                return redirect(url_for('dash2'))
        else:
            msg = 'Please enter correct email / password !'
    return render_template('login.html', msg=msg)


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'value' in request.form and 'category' in request.form:
        username = request.form['username']
        password = request.form['password']
        followers=request.form['value']
        category=request.form['category']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM login WHERE username = %s and category=%s', (username,category, ))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists !'
        else:
            cursor.execute('INSERT INTO login VALUES  (%s, %s,%s,%s)',(username, password,category,followers ))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg=msg)

@app.route('/register1', methods=['GET', 'POST'])
def register1():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'value' in request.form and 'category' in request.form:
        username = request.form['username']
        password = request.form['password']
        cname=request.form['value']
        category=request.form['category']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM login WHERE username = %s and category=%s', (username,category, ))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists !'
        else:
            cursor.execute('INSERT INTO login VALUES  (%s, %s,%s,%s)',(username, password,category,cname ))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register1.html', msg=msg)

@app.route('/register2', methods=['GET', 'POST'])
def register2():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and  'category' in request.form:
        username = request.form['username']
        password = request.form['password']
        cname='null'
        category=request.form['category']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(
            'SELECT * FROM login WHERE username = %s and category=%s', (username,category, ))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists !'
        else:
            cursor.execute('INSERT INTO login VALUES  (%s, %s,%s,%s)',(username, password,category,cname ))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register2.html', msg=msg)

@app.route('/monthly_report')
def monthly_report():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM campaign WHERE MONTH(date) = MONTH(CURDATE()) AND YEAR(date) = YEAR(CURDATE())')
    campaigns = cursor.fetchall()
    cursor.close()
    return render_template('monthly_report.html', campaigns=campaigns)





@app.route('/dash2',methods=['GET','POST'])
def dash2():
    n='null'
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('select * from rinfluencer ')
    rcampaigns = cursor.fetchall()
    cursor.execute('select * from admin where username=%s and value!=%s',(session['username'],n,))
    admin=cursor.fetchall()
    cursor.execute('SELECT campaign.* FROM campaign JOIN admin ON campaign.name = admin.name')
    campaigns=cursor.fetchall()
    return render_template('dash2.html',rcampaigns=rcampaigns,admin=admin,campaigns=campaigns)

@app.route('/find2',methods=['GET','POST'])
def find2():
    i='Influencer'
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('select * from login where category=%s',(i,))
    influencer=cursor.fetchall()
    cursor.execute('select * from campaign')
    campaigns=cursor.fetchall()
    return render_template('find2.html',influencer=influencer,campaigns=campaigns)


@app.route('/flag',methods=['GET','POST'])
def flag():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    name=request.form['campaign']
    value='null'
    cursor.execute('insert into admin(username,name,value) values (%s,%s,%s)',(session['username'],name,value))
    mysql.connection.commit()
    return redirect(url_for('find2'))

@app.route('/flag1',methods=['GET','POST'])
def flag1():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    name=request.form['influencer']
    value=request.form['value']
    cursor.execute('insert into admin(username,name,value) values (%s,%s,%s)',(session['username'],name,value))
    mysql.connection.commit()
    return redirect(url_for('find2'))

@app.route('/remove_admin', methods=['GET'])
def remove_admin():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    name = request.args.get('name')  
    cursor.execute('DELETE FROM admin WHERE name=%s', (name,))
    mysql.connection.commit()
    return redirect(url_for('dash2'))


@app.route('/remove',methods=['GET','POST'])
def remove():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    name = request.args.get('name')  
    cursor.execute('DELETE FROM admin WHERE name=%s', (name,))
    mysql.connection.commit()
    return redirect(url_for('dash2'))

@app.route('/status2', methods=['GET', 'POST'])
def status2():
    cache_key = 'status2_campaign_statuses'
    campaign_statuses = get_cached_data(cache_key)

    if not campaign_statuses:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT campaign, sdate, date FROM rcampaigns')
        campaigns = cursor.fetchall()

        campaign_statuses = []
        for campaign in campaigns:
            start_date = campaign['sdate']
            end_date = campaign['date']
            total_days = (end_date - start_date).days
            completed_days = (datetime.now().date() - start_date).days
            completed_days = max(min(completed_days, total_days), 0)

            campaign_statuses.append({
                'name': campaign['campaign'],
                'completed': completed_days,
                'incomplete': total_days - completed_days
            })

        set_cache_data(cache_key, campaign_statuses)

    return render_template('status2.html', campaigns=parse_dates(campaign_statuses))


@app.route('/dash', methods=['GET', 'POST'])
def dash():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('select * from influencer where username=%s', (session['username'],))
    campaigns = cursor.fetchall()
    cursor.execute('select * from rinfluencer where username=%s', (session['username'],))
    rcampaigns = cursor.fetchall()
    return render_template('dash.html', campaigns=campaigns, rcampaigns=rcampaigns)



@app.route('/accept_campaign', methods=['GET'])
def accept_campaign():
    campaign = request.args.get('campaign_id')
    sdate=datetime.now().date()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM influencer WHERE campaign = %s', (campaign,))
    register = cursor.fetchone()
    if register:
        username = register.get('username')
        desp = register.get('desp')
        date = register.get('date')
        budget = register.get('budget')
        cname = register.get('cname')
        u=register.get('u')
        cursor.execute('INSERT INTO rinfluencer (username, campaign, desp, date, budget, cname,sdate) VALUES (%s, %s, %s, %s, %s, %s,%s)', 
                       (username, campaign, desp, date, budget, cname,sdate))
        cursor.execute('INSERT INTO rcampaigns (username,influencer ,campaign,sdate,date) VALUES (%s, %s, %s, %s,%s)', 
                       (u,username, campaign, sdate,date))
        cursor.execute('DELETE FROM influencer WHERE campaign = %s', (campaign,))
        mysql.connection.commit()
    return redirect(url_for('dash'))


@app.route('/reject_campaign', methods=['GET'])
def reject_campaign():
    campaign = request.args.get('campaign_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM influencer WHERE campaign = %s', (campaign,))
    mysql.connection.commit()
    return redirect(url_for('dash'))

@app.route('/request_company', methods=['POST', 'GET'])
def request_company():
    if request.method == 'POST':
        campaign = request.form['campaign']
        username=request.form['username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM login WHERE username = %s', (session['username'],))
        campaigns = cursor.fetchone()
        if campaigns:
            followers = campaigns.get('value')
            cursor.execute('INSERT INTO ncampaigns (username, influencer, followers, campaign) VALUES (%s, %s, %s, %s)', (username, session['username'], followers, campaign))
            mysql.connection.commit()
        else:
            return 'No campaigns found for this company'
    return redirect(url_for('find'))

@app.route('/accept_influencer', methods=['GET'])
def accept_influencer():
    campaign = request.args.get('campaign_id')
    sdate = datetime.now().date()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    
    query = '''
        SELECT ncampaigns.username, ncampaigns.influencer, campaign.date AS end_date,campaign.cname AS cname,campaign.budget AS budget,campaign.desp AS desp
        FROM ncampaigns
        JOIN campaign ON ncampaigns.campaign = campaign.name
        WHERE ncampaigns.campaign = %s
    '''
    cursor.execute(query, (campaign,))
    register = cursor.fetchone()

    if register:
        username = register.get('username')
        influencer = register.get('influencer')
        end_date = register.get('end_date')
        desp=register.get('desp')
        budget=register.get('budget')
        cname=register.get('cname')
        cursor.execute('INSERT INTO rcampaigns (username, influencer, campaign, sdate, date) VALUES (%s, %s, %s, %s, %s)', 
                       (username, influencer, campaign, sdate, end_date))
        cursor.execute('INSERT INTO rinfluencer (username, campaign,desp,date,budget,cname ,sdate) VALUES (%s, %s, %s, %s, %s,%s,%s)', 
                       (influencer, campaign,desp,end_date,budget,cname ,sdate ))
        cursor.execute('DELETE FROM ncampaigns WHERE campaign = %s', (campaign,))
        mysql.connection.commit()
    
    return redirect(url_for('dash1'))



@app.route('/reject_influencer', methods=['GET'])
def reject_influencer():
    campaign = request.args.get('campaign_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM ncampaigns WHERE campaign = %s', (campaign,))
    mysql.connection.commit()
    return redirect(url_for('dash1'))



@app.route('/Request_influencer', methods=['POST', 'GET'])
def Request_influencer():
    if request.method == 'POST':
        influencer = request.form['influencer']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM campaign WHERE username = %s', (session['username'],))
        campaigns = cursor.fetchall()
        if campaigns:
            for campaign in campaigns:
                campaign_name = campaign.get('name')
                desp = campaign.get('desp')
                date = campaign.get('date')
                budget = campaign.get('budget')
                cname = campaign.get('cname')
                cursor.execute('INSERT INTO influencer (username, campaign, desp, date, budget, cname,u) VALUES (%s, %s, %s, %s, %s, %s,%s)', 
                               (influencer, campaign_name, desp, date, budget, cname,session['username']))
            mysql.connection.commit()
        else:
            return 'No campaigns found for this company'
    return redirect(url_for('find1'))





@app.route('/find', methods=['GET', 'POST'])
def find():
    cache_key = 'find_campaigns'
    campaigns = get_cached_data(cache_key)

    if not campaigns:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('select * from campaign')
        campaigns = cursor.fetchall()
        set_cache_data(cache_key, campaigns)

    return render_template('find.html', campaigns=parse_dates(campaigns))




@app.route('/status', methods=['GET', 'POST'])
def status():
    cache_key = f'status_{session["username"]}'
    campaign_statuses = get_cached_data(cache_key)

    if not campaign_statuses:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT campaign, desp, sdate, date FROM rinfluencer WHERE username = %s', (session['username'],))
        campaigns = cursor.fetchall()

        campaign_statuses = []
        for campaign in campaigns:
            start_date = campaign['sdate']
            end_date = campaign['date']
            total_days = (end_date - start_date).days
            completed_days = (datetime.now().date() - start_date).days
            completed_days = max(min(completed_days, total_days), 0)

            campaign_statuses.append({
                'name': campaign['campaign'],
                'completed': completed_days,
                'incomplete': total_days - completed_days
            })

        set_cache_data(cache_key, campaign_statuses)

    return render_template('status.html', campaigns=parse_dates(campaign_statuses))


@app.route('/dash1',methods=['GET','POST'])
def dash1():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('select * from ncampaigns where username=%s',(session['username'],))
    new_campaigns=cursor.fetchall()
    cursor.execute('select * from rcampaigns where username=%s',(session['username'],))
    register=cursor.fetchall()
    return render_template('dash1.html',new_campaigns=new_campaigns,register=register)


    return render_template('dash1.html', new_campaigns=dash1_data['new_campaigns'], register=dash1_data['register'])
@app.route('/save_campaign', methods=['POST'])
def save_campaign():
    campaign_name = request.form['campaignName']
    description = request.form['description']
    date = request.form['date']
    budget = request.form['budget']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('insert into campaign values(%s,%s,%s,%s,%s,%s)',(campaign_name,description,date,budget,session['username'],session['value']))
    mysql.connection.commit()
    return redirect(url_for('campaigns'))

@app.route('/campaigns',methods=['POST','GET'])
def campaigns():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('select * from campaign where username=%s',(session['username'],))
    campaigns=cursor.fetchall() 
    return render_template('campaigns.html',campaigns=campaigns)

@app.route('/edit_campaign', methods=['POST'])
def edit_campaign():
    old_name = request.form['campaignName']
    new_name = request.form['newCampaignName']
    budget = request.form['budget']

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE campaign SET name=%s, budget=%s WHERE name=%s AND username=%s', (new_name, budget, old_name, session['username']))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('campaigns'))

@app.route('/edit_sponsor', methods=['POST'])
def edit_sponsor():
    old_name = request.form['sponsorName']
    new_name = request.form['newName']

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE sponsor SET name=%s WHERE name=%s AND username=%s', (new_name, old_name, session['username']))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('sponsors'))




@app.route('/delete_campaign',methods=['POST','GET'])
def delete_campaign():
    name = request.args.get('campaign')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('delete from campaign where name=%s',(name,))
    mysql.connection.commit()
    return redirect(url_for('campaigns'))

@app.route('/find1',methods=['GET','POST'])
def find1():
    i='Influencer'
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('select * from login where category=%s',(i,))
    influencers=cursor.fetchall()
    return render_template('find1.html',influencers=influencers)


@app.route('/status1', methods=['GET', 'POST'])
def status1():
    cache_key = f'status1_{session["username"]}'
    campaign_statuses = get_cached_data(cache_key)

    if not campaign_statuses:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT campaign, sdate, date FROM rcampaigns WHERE username = %s', (session['username'],))
        campaigns = cursor.fetchall()

        campaign_statuses = []
        for campaign in campaigns:
            start_date = campaign['sdate']
            end_date = campaign['date']
            total_days = (end_date - start_date).days
            completed_days = (datetime.now().date() - start_date).days
            completed_days = max(min(completed_days, total_days), 0)

            campaign_statuses.append({
                'name': campaign['campaign'],
                'completed': completed_days,
                'incomplete': total_days - completed_days
            })

        set_cache_data(cache_key, campaign_statuses)

    return render_template('status1.html', campaigns=parse_dates(campaign_statuses))



@app.route('/clear_cache')
def clear_cache():
    cache.flushdb()
    return 'Cache cleared!'


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('email', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run()
    os.execv(__file__, sys.argv)