'''
Flask app for TalkingPotatoes project
'''

import uuid
import json
import validators
from passlib.hash import sha256_crypt
from flask import Flask, request, render_template
from flask_httpauth import HTTPBasicAuth
import thumbtack_conn
import db
import analytics
import helper
import fb_helper

def create_app(config):
    """
    wrapper function that instantiates Flask app
    """
    app = Flask(__name__)
    auth = HTTPBasicAuth()

    app.config.from_pyfile(config)

    database_url = app.config['DATABASE_URL']
    db_obj = db.Database(database_url)

    analytics_obj = analytics.Analytics(database_url)


    @auth.verify_password
    def verify_password(username, password):
        """Password verification for users of our service

        :param string username: user username
        :param string password: user password
        :return string username: user username
        """
        user = json.loads(
            db_obj.get_data(db_schema='talking_potato', table_name='users',
                            filter_data={'username': username}))
        if len(user) > 0 and sha256_crypt.verify(password, user[0]['password']):
            return username
        return None


    @app.route("/")
    def hello_world():
        """
        a health check

        :return "string health check"
        """
        # result = db_obj.get_all_leads()
        # df_thumbtack = pd.DataFrame(list(result.fetchall()))
        # return df_thumbtack.to_json(orient="records")
        return "Hello from Talking Potatoes!!!"
        #return render_template("home.html")


    @app.route("/dummy_thumbtack_lead", methods=["GET"])
    def create_dummy_data():
        """Create thumbtack lead dummy data

        :return tuple: a tuple containing
            dict dummy_dict: a thumbtack example lead
            int: response status code
        """
        dummy_dict = thumbtack_conn.create_test_data()
        data, column_names = thumbtack_conn.thumbtack_lead_json_to_list(dummy_dict)
        db_obj.insert_row_from_lead_list("thumbtack", "leads", data, column_names)

        return dummy_dict, 200


    @app.route("/thumbtack_lead", methods=["POST"])
    @auth.login_required
    def receive_lead():
        """receive a thumbtack lead and insert into db

        :return tuple: a tuple containing
            dict: the response status details
            int: response status code
        """
        if request.json is not None:
            data, column_names = thumbtack_conn.thumbtack_lead_json_to_list(request.json)
            db_obj.insert_row_from_lead_list("thumbtack", "leads", data, column_names)
            return {"status": "success"}, 200
        return {"status": "fail", "details": "empty json"}, 400


    @app.route("/thumbtack_messages", methods=["POST"])
    @auth.login_required
    def receive_message():
        """receive a thumbtack message and insert into db

        :return tuple: a tuple containing
            dict: the response status details
            int: response status code
        """
        if request.json is not None:
            data, column_names = thumbtack_conn.thumbtack_message_json_to_list(request.json)
            db_obj.insert_row_from_message_list("thumbtack", "messages", data, column_names)
            return {"status": "success"}, 200
        return {"status": "fail", "details": "empty json"}, 400

    @app.route("/register", methods=["POST", "PUT", "DELETE"])
    def register():
        """register a new user of our service

        :return tuple: a tuple containing
            dict: status description
            int: response status code
        """
        status = None
        email = request.args.get("email")
        username = request.args.get("username")
        password = request.args.get("password")
        if request.method == "POST":
            email_query = json.loads(db_obj.get_data(db_schema='talking_potato',
                                                    table_name='users',
                                                    filter_data={'email': email}))
            name_query = json.loads(db_obj.get_data(db_schema='talking_potato',
                                                    table_name='users',
                                                    filter_data={'username': username}))

            if not validators.email(email):
                status = {'status': 'bad email'}, 400
            elif len(username) < 3:
                status = {'status': 'username too short'}, 400
            elif not password:
                status = {'status': 'password must be entered'}, 400
            elif len(password) < 6:
                status = {'status': 'password too short'}, 400
            elif not username.isalnum():
                status = {'status': 'username must be alphanumeric'}, 400
            elif len(email_query) > 0:
                status = {'status': 'email already registered'}, 400
            elif len(name_query) > 0:
                status = {'status': 'username already registered'}, 400
            if status:
                return status

            password_hash = sha256_crypt.encrypt(password)
            entry = {'user_id': str(uuid.uuid4()), 'username': username,
                    'password': password_hash, 'email': email}
            if request.args.get('phone_number'):
                entry['phone_number'] = request.args.get("phone_number")
            if request.args.get('thumbtack_user_id') and request.args.get('thumbtack_password') \
                and request.args.get('thumbtack_business_id'):
                entry['thumbtack_user_id'] = request.args.get('thumbtack_user_id')
                entry['thumbtack_password'] = request.args.get('thumbtack_password')
                entry['thumbtack_business_id'] = request.args.get('thumbtack_business_id')
            if request.args.get('fb_app_id') and request.args.get('fb_page_id') \
               and request.args.get('fb_page_access_token') and request.args.get('fb_secret_key'):
                entry['fb_app_id'] = request.args.get('fb_app_id')
                entry['fb_page_id'] = request.args.get('fb_page_id')
                entry['fb_page_access_token'] = request.args.get('fb_page_access_token')
                entry['fb_secret_key'] = request.args.get('fb_secret_key')
            db_obj.insert_row('talking_potato', 'users', entry)

        else:
            if not password:
                return {'status': 'fail', "details": "must enter password"}, 400
            if email:
                email_query = json.loads(db_obj.get_data(db_schema='talking_potato',
                                                         table_name='users',
                                                         filter_data={'email': email}))
                if sha256_crypt.verify(password, email_query[0]["password"]):
                    if request.method == "PUT":
                        values_to_update = request.args.to_dict()
                        values_to_update.pop("password")
                        db_obj.update("talking_potato", "users", values_to_update, "email")
                    elif request.method == "DELETE":
                        entry = {"email": email}
                        db_obj.delete_by_template("talking_potato", "users", entry)
                else:
                    return {'status': 'fail',
                            "details": "password does not match registered user"}, 400
            elif username:
                name_query = json.loads(db_obj.get_data(db_schema='talking_potato',
                                                    table_name='users',
                                                    filter_data={'username': username}))
                if sha256_crypt.verify(password, name_query[0]["password"]):
                    if request.method == "PUT":
                        values_to_update = request.args.to_dict()
                        values_to_update.pop("password")
                        db_obj.update("talking_potato", "users", values_to_update, "username")
                    elif request.method == "DELETE":
                        entry = {"username": username}
                        db_obj.delete_by_template("talking_potato", "users", entry)
                else:
                    return {'status': 'fail',
                            "details": "password does not match registered user"}, 400
            else:
                return {'status': 'fail', "details": "must enter email or username"}, 400
        return {'status': 'success'}, 200


    def verify_webhook(req, username):
        """webhook verification required by facebook

        :param flask.Request req: the flask request object
        :param username: the username
        :return string: either the challenge received by facebook, or http status 400
        """
        query = json.loads(db_obj.get_data(db_schema='talking_potato',
                                           table_name='users', filter_data={'username': username}))
        verify_token = query[0]['fb_app_secret_key']
        token = req.args.get('hub.verify_token')
        challenge = req.args.get('hub.challenge')
        if token == verify_token:
            print('verified')
            return str(challenge)
        return '400'


    @app.route("/fb_lead", methods=['GET', 'POST'])
    @auth.login_required
    def webhook():
        """receive a fb message and insert it into db

        :return tuple: a tuple containing
            dict data: the fb message data that was received
            int: response status code
        """
        if request.method == 'GET':
            status = verify_webhook(request, auth.current_user())

        elif request.method == 'POST':
            payload = request.json
            event = payload['entry'][0]['messaging']
            for msg in event:
                if fb_helper.is_user_message(msg):
                    text = msg['message']['text']
                    temp = {'text': text}
                    msg['message_id'] = msg['message']['mid']
                    msg['message'] = temp
                    msg['page_id'] = payload['entry'][0]['id']
                    msg['update_time'] = payload['entry'][0]['time']
                    flat_msg = helper.flatten_json(msg)
                    flat_msg['update_time'] = helper.convert_epoch_milliseconds_to_datetime_string(
                        flat_msg['update_time'])
                    flat_msg['timestamp'] = helper.convert_epoch_milliseconds_to_datetime_string(
                        flat_msg['timestamp'])

                    db_obj.insert_row('fb', 'messages', flat_msg)
            status = 200

        else:
            status = 200

        return status


    @app.route("/get_messages", methods=['GET'])
    @auth.login_required
    def get_messages():
        """return the messages for a date range and lead source(s).

        :query param lead_source: lead source to filter by. If none, queries all lead sources.
        :query param date: contacted date to query.

        :return list result: a list of json messages
        """
        username = auth.current_user()
        user = json.loads(db_obj.get_data(db_schema='talking_potato',
                                           table_name='users', filter_data={'username': username}))
        filter_data = {}
        lead_source = request.args.get('lead_source')
        date = request.args.get('date')
        if date:
            date = date.replace("'", "")
            date_format_check = helper.check_date_format(date)
            if not date_format_check:
                return 'Please enter the date in YYYY-MM-DD format'
        if lead_source:
            lead_source = lead_source.replace("'", "")
            if lead_source == "facebook":
                schema = "fb"
                if date:
                    filter_data['date(timestamp)'] = date
                filter_data["page_id"] = user[0]["fb_page_id"]
            elif lead_source == "thumbtack":
                schema = "thumbtack"
                if date:
                    filter_data['date(contacted_time)'] = date
                filter_data["thumbtack_business_id"] = user[0]["thumbtack_business_id"]
            result = db_obj.get_data(db_schema=schema, table_name='messages',
                                     filter_data=filter_data)
        else:
            filter_data["page_id"] = user[0]["fb_page_id"]
            if date:
                filter_data['date(timestamp)'] = date
            result = db_obj.get_data(db_schema="fb", table_name='messages',
                                 filter_data=filter_data)
            filter_data.pop('page_id')
            if 'date(timestamp)' in filter_data:
                filter_data.pop('date(timestamp)')


            filter_data["thumbtack_business_id"] = user[0]["thumbtack_business_id"]
            if date:
                filter_data['date(contacted_time)'] = date
            result += db_obj.get_data(db_schema="thumbtack", table_name='messages',
                                      filter_data=filter_data)
        return result

    @app.route("/get_leads", methods=['GET'])
    @auth.login_required
    def get_leads():
        """return the leads for a date range and lead source(s).

        :query param lead_source: lead source to filter by. If none, queries all lead sources.
            -currently only thumbtack
        :query param date: contacted date to query.

        :return list result: a list of json leads
        """
        username = auth.current_user()
        user = json.loads(db_obj.get_data(db_schema='talking_potato',
                                           table_name='users', filter_data={'username': username}))
        filter_data = {'thumbtack_business_id': user[0]['thumbtack_business_id']}
        date = request.args.get('date')

        if date:
            date = date.replace("'", "")
            date_format_check = helper.check_date_format(date)
            if not date_format_check:
                return 'Please enter the date in YYYY-MM-DD format'
            filter_data['date(contacted_time)'] = date
        result = db_obj.get_data(db_schema='thumbtack', table_name='leads', filter_data=filter_data)
        return result


    @app.route("/message_analytics", methods=['GET'])
    @auth.login_required
    def get_message_analytics():
        """return a count of messages for a date range and lead source(s).

        :query param from_date: beginning date to filter by. Optional.
        :query param to_date: ending date to filter by. Optional.
        :query param lead_source: lead source to filter data by. Optional

        :return list result: a list of dicts with keys: date, count, optional user_source
        """

        username = auth.current_user()
        query = json.loads(db_obj.get_data(db_schema='talking_potato',
                                           table_name='users', filter_data={'username': username}))

        filter_user_date_range = {'user_id': query[0]['user_id']}
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        filter_data = {'date(contacted_time)': 1}
        filter_data['user_source'] = 1

        from_date, to_date = analytics_obj.create_dates('all', request.args.get('from_date'),
                                                        request.args.get('to_date'))
        if from_date is None or to_date is None:
            return 'Please enter the date in YYYY-MM-DD format'

        filter_user_date_range['from_date'] = from_date
        filter_user_date_range['to_date'] = to_date

        result = analytics_obj.get_grouped_by_date(db_schema='talking_potato',
                                                   table_name='messages',
                                                   filter_data=filter_data,
                                                   filter_user_date_range=filter_user_date_range)
        return result

    @app.route("/lead_analytics", methods=['GET'])
    @auth.login_required
    def get_lead_analytics():
        """return a count of leads for a date range and lead source(s). (currently on thumbtack)

        :query param from_date: beginning date to filter by. Optional.
        :query param to_date: ending date to filter by. Optional.
        :query param dimension: dimension to filter data by. (currently only state and count)

        :return result: a list of dicts with keys: date, optional category, optimal state, count.
        """
        username = auth.current_user()
        user = json.loads(db_obj.get_data(db_schema='talking_potato',
                                           table_name='users', filter_data={'username': username}))

        filter_user_date_range = {'thumbtack_business_id': user[0]['thumbtack_business_id']}

        dimension = request.args.get('dimension')

        filter_data = {'date(contacted_time)': 1}

        if dimension:
            if dimension in ('category', 'state', 'travel_preferences'):
                filter_data[dimension] = 1
            else:
                return 'Accepted values of dimension = category, state, or travel_preferences'

        from_date, to_date = analytics_obj.create_dates('all', request.args.get('from_date'),
                                                        request.args.get('to_date'))
        if from_date is None or to_date is None:
            return 'Please enter the date in YYYY-MM-DD format'

        filter_user_date_range['from_date'] = from_date
        filter_user_date_range['to_date'] = to_date
        result = analytics_obj.get_grouped_by_date(db_schema='thumbtack',
                                                   table_name='leads',
                                                   filter_data=filter_data,
                                                   filter_user_date_range=filter_user_date_range)
        return result

    @app.route("/message_analytics/trends", methods=['GET'])
    @auth.login_required
    def get_message_analytics_trends():
        """
        message analytics: trends

        :query param frequency: days, weeks, months, years
            TODO: days, weeks
        :query param from_date: starting date to get message counts
        :query param to_date: ending date to get message counts
        :query param lead_source: facebook or thumbtack. for both, none
        :query param dimension: dimension to filter by, if lead source is not none
        :query param data_format: if graph, must be dimensionless

        :return counts: a dictionary that will show counts of messages for time ranges

        """
        username = auth.current_user()
        user = json.loads(db_obj.get_data(db_schema='talking_potato',
                                           table_name='users', filter_data={'username': username}))

        frequency = request.args.get('frequency')
        lead_source = request.args.get('lead_source')
        dimension = request.args.get('dimension')

        if not frequency or (frequency==""):
            frequency = "years"

        from_date, to_date = analytics_obj.create_dates(frequency, request.args.get('from_date'),
                                                        request.args.get('to_date'))
        data_format = request.args.get('data_format')

        if data_format == 'graph':
            if dimension is not None and dimension != '':
                return {"status": "fail",
                        "details": "if graph format, dimension should be None"}, 400

        if from_date is None or to_date is None:
            if frequency == "years":
                return 'Please enter the date in YYYY format'
            return 'Please enter the date in YYYY-MM format'

        from_year = int(from_date.split("-")[0])
        to_year = int(to_date.split("-")[0])

        if frequency == "years":
            counts = analytics_obj.get_message_counts_per_year(user[0], lead_source, dimension,
                                                               from_year, to_year, data_format)
        elif frequency == "months":
            from_month = int(from_date.split("-")[1])
            to_month = int(to_date.split("-")[1])
            counts = analytics_obj.get_message_counts_per_month(user[0], lead_source, dimension,
                                                                from_year, to_year,
                                                                from_month, to_month, data_format)

        return counts

    return app

# if __name__ == '__main__':
app = create_app('config.py')
# app.run(debug=True)

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000)
