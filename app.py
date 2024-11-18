from flask import Flask, render_template, request, Response
from flask_paginate import Pagination, get_page_args
from flask_socketio import SocketIO
from flask_mqtt import Mqtt

import csv
import io
import json
import sqlite3
import xlwt

from datetime import datetime


app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = '192.168.0.103'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = 'user'
app.config['MQTT_PASSWORD'] = 'user'
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False
app.config['MQTT_LAST_WILL_TOPIC'] = 'LastWill'
app.config['MQTT_LAST_WILL_MESAGE'] = 'See you in hell'

socketio = SocketIO(app)
mqtt = Mqtt(app, connect_async=True)


@app.route('/')
def default():
    return render_template('index.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/th_data')
def th_data():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM th_sensor_data')
    rows = cursor.fetchall()
    connection.close()
    return rows

@app.route('/th_data_paged')
def th_data_paged():
    # page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    page = int(request.args.get('page', 1))
    per_page = 100
    offset = (page - 1) * per_page
    
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM th_sensor_data')
    rows = cursor.fetchall()
    connection.close()
    total = len(rows)
    limited_rows = rows[offset:offset + per_page]
    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')
    return render_template('th_data_paged.html', rows=limited_rows, page=page, per_page=per_page, pagination=pagination)

@app.route('/th_samples')
def th_samples():
    page = 1
    page_arg = request.args['page']
    if page_arg:
        page = int(page_arg)
    
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM th_sensor_data')
    rows = cursor.fetchall()
    connection.close()
    total = len(rows)
    from_idx = (page - 1) * 100
    to_idx = page * 100
    samples = rows[from_idx:to_idx]
    return samples


@app.route('/download/excel')
def download_excel():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM th_sensor_data')
    th_rows = cursor.fetchall()
    cursor.execute('SELECT * FROM aiq_sensor_data')
    aiq_rows = cursor.fetchall()
    connection.close()
    
    output = io.BytesIO()
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('temperature and humidity')    
    sheet.write(0, 0, 'Timestamp')
    sheet.write(0, 1, 'Temperature')
    sheet.write(0, 2, 'Humidity')
    
    i = 1
    for row in th_rows:
        timestamp = str(row[0])
        temperature = row[1]
        humidity = row[2]
        sheet.write(i, 0, timestamp)
        sheet.write(i, 1, temperature)
        sheet.write(i, 2, humidity)
        i += 1
        
    sheet = workbook.add_sheet('air quality')    
    sheet.write(0, 0, 'Timestamp')
    sheet.write(0, 1, 'CO2')
    sheet.write(0, 2, 'TVOC')
    
    i = 1
    for row in aiq_rows:
        timestamp = str(row[0])
        co2 = row[1]
        tvoc = row[2]
        sheet.write(i, 0, timestamp)
        sheet.write(i, 1, co2)
        sheet.write(i, 2, tvoc)
        i += 1
        
    workbook.save(output)
    output.seek(0)
    
    return Response(output, mimetype="application/ms-excel", 
                    headers={"Content-Disposition": "attachment;filename=sensors_data.xls"})


@app.route('/download/csv')
def download_csv():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('SELECT * FROM th_sensor_data')
    rows = cursor.fetchall()
    connection.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    line = ['Timestamp', 'Temperature', 'Humidity']
    writer.writerow(line)
    
    for row in rows:
        timestamp = str(row[0])
        temperature = str(row[1])
        humidity = str(row[2])
        line = [timestamp, temperature, humidity]
        writer.writerow(line)
    
    output.seek(0)
    
    return Response(output, mimetype="text/csv", 
                    headers={"Content-Disposition": "attachment;filename=th_sensor_data.csv"})


@app.route('/reports')
def reports():
    return render_template('reports.html')


@mqtt.on_connect()
def handle_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print('connected to MQTT broker')
        mqtt.subscribe('sensors/th')
        mqtt.subscribe('sensors/aiq')
    else:
        print('could not connect to MQTT broker ({})'.format(rc))

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    if message.topic == 'sensors/th':
        json_data = message.payload.decode()
        data = json.loads(json_data)
        temperature = data['temperature']
        humidity = data['humidity']        
        store_th_data(json_data)
        socketio.emit('sensor_th_data', json.dumps({'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                    'temperature': temperature, 'humidity': humidity}))
    if message.topic == 'sensors/aiq':
        json_data = message.payload.decode()
        data = json.loads(json_data)
        co2 = data['CO2']
        tvoc = data['eTVOC']        
        store_aiq_data(json_data)
        socketio.emit('sensor_aiq_data', json.dumps({'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                                    'co2': co2, 'tvoc': tvoc}))
def store_th_data(json_data):
    data = json.loads(json_data)
    temperature = data['temperature']
    humidity = data['humidity']
    print('temperature {}, humidity {}'.format(temperature, humidity))
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('INSERT INTO th_sensor_data (temperature, humidity) VALUES(?, ?)', (temperature, humidity))
    connection.commit()
    connection.close()

def store_aiq_data(json_data):
    data = json.loads(json_data)
    co2 = data['CO2']
    tvoc = data['eTVOC']
    print('CO2 {}, TVOC {}'.format(co2, tvoc))
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('INSERT INTO aiq_sensor_data (co2, tvoc) VALUES(?, ?)', (co2, tvoc))
    connection.commit()
    connection.close()

if __name__ == '__main__':
    # app.run(debug=True)
    socketio.run(app, debug=True)