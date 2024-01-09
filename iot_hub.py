import sqlite3
import json
import random

from flask import Flask, render_template, request, abort, jsonify
from flask_mqtt import Mqtt

app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = 'broker.emqx.io'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False

mqtt_client = Mqtt(app)

@mqtt_client.on_connect()
def handle_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        print('successfully connected to MQTT broker')
        mqtt_client.subscribe('environmental')
        mqtt_client.subscribe('aiq')
    else:
        print('could not connect to MQTT broker. code: ', rc)

@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    if message.topic == 'aiq':
        store_aiq_data(message.payload.decode())
    if message.topic == 'environmental':
        store_environmental_data(message.payload.decode())


def store_aiq_data(json_data):
    data = json.loads(json_data)
    tvoc = data['TVOC']
    eco2 = data['eCO2']
    print(f'AIQ data: TVOC = {tvoc}, eCO2 = {eco2}')
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()
    cursor.execute("INSERT INTO aiq_data(timestamp, tvoc, eco2) VALUES(datetime('now'), (?), (?))", (tvoc, eco2))
    connection.commit()
    connection.close()
    
def store_environmental_data(json_data):
    data = json.loads(json_data)
    temperature = data['temperature']
    humidity = data['humidity']
    print(f'Environmental data: temperature = {temperature}, humidity = {humidity}')
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()
    cursor.execute("INSERT INTO environmental_data(timestamp, temperature, humidity) VALUES(datetime('now'), (?), (?))", (temperature, humidity))
    connection.commit()
    connection.close()

def load_environmental_data():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()
    # for row in cursor.execute("SELECT * FROM environmental_data ORDER BY timestamp DESC"):
    #    timestamp = str(row[0])
    #     temperature = row[1]
    #     humidity = row[2]
    
    cursor.execute("SELECT * FROM environmental_data ORDER BY timestamp DESC LIMIT 1")
    result = cursor.fetchone()
    connection.close()
    if result is not None:
        timestamp = str(result[0])
        temperature = result[1]
        humidity = result[2]
        return timestamp, temperature, humidity
    return "", "", ""

def load_aiq_data():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM aiq_data ORDER BY timestamp DESC LIMIT 1")
    result = cursor.fetchone()
    connection.close()
    if result is not None:
        timestamp = str(result[0])
        tvoc = result[1]
        eco2 = result[2]
        return timestamp, tvoc, eco2
    return "", "", ""

@app.route("/environmental")
def environmental():
    timestamp, temperature, humidity = load_environmental_data()
    if timestamp and temperature and humidity:
        template_data = {
            'timestamp': timestamp,
            'temperature': temperature,
            'humidity': humidity
        }
        return render_template('environmental.html', **template_data)
    template_data = {
        'description': 'environmental'
    }
    return render_template('nodata.html', **template_data)

@app.route("/get_environmental_data")
def get_environmental_data():
    timestamp, temperature, humidity = load_environmental_data()
    if timestamp and temperature and humidity:
        data = {
            'timestamp': timestamp,
            'temperature': temperature,
            'humidity': humidity
        }
        return jsonify(data)

@app.route("/aiq")
def aiq():
    timestamp, tvoc, eco2 = load_aiq_data()
    if timestamp and tvoc and eco2:
        template_data = {
            'timestamp': timestamp,
            'tvoc': tvoc,
            'eco2': eco2
        }
        return render_template('aiq.html', **template_data)
    template_data = {
        'description': 'air quqlity'
    }
    return render_template('nodata.html', **template_data)

@app.route("/get_aiq_data")
def get_aiq_data():
    timestamp, tvoc, eco2 = load_aiq_data()
    if timestamp and tvoc and eco2:
        data = {
            'timestamp': timestamp,
            'tvoc': tvoc,
            'eco2': eco2
        }
        return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)