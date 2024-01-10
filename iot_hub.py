import sqlite3
import json
import random

from flask import Flask, render_template, request, abort, jsonify, send_file, make_response
from flask_mqtt import Mqtt

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io

app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = 'broker.emqx.io'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False

mqtt_client = Mqtt(app, connect_async=True)

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

def load_last_environmental_sample():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()  
    cursor.execute("SELECT * FROM environmental_data ORDER BY timestamp DESC LIMIT 1")
    result = cursor.fetchone()
    connection.close()
    if result is not None:
        timestamp = str(result[0])
        temperature = result[1]
        humidity = result[2]
        return timestamp, temperature, humidity
    return "", "", ""

def load_temperature_samples():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()  
    cursor.execute("SELECT timestamp, temperature FROM environmental_data ORDER BY timestamp")
    result = cursor.fetchall()
    connection.close()
    timestamps = []
    samples = []
    for row in result:
        timestamps.append(row[0])
        samples.append(row[1])
    return timestamps, samples

def load_humidity_samples():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()  
    cursor.execute("SELECT timestamp, humidity FROM environmental_data ORDER BY timestamp")
    result = cursor.fetchall()
    connection.close()
    timestamps = []
    samples = []
    for row in result:
        timestamps.append(row[0])
        samples.append(row[1])
    return timestamps, samples

def num_environmental_samples():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()  
    cursor.execute("SELECT COUNT(*) FROM environmental_data")
    result = cursor.fetchone()
    connection.close()
    if result is not None:
        return result[0]
    return 0

def num_aiq_samples():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()  
    cursor.execute("SELECT COUNT(*) FROM aiq_data")
    result = cursor.fetchone()
    connection.close()
    if result is not None:
        return result[0]
    return 0

def load_environmental_data():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()  
    cursor.execute("SELECT * FROM environmental_data ORDER BY timestamp LIMIT " + str(num_samples))
    result = cursor.fetchall()
    connection.close()
    if result is not None:
        timestamp = str(result[0])
        temperature = result[1]
        humidity = result[2]
        return timestamp, temperature, humidity
    return "", "", ""

def load_tvoc_samples():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()
    cursor.execute("SELECT timestamp, tvoc FROM aiq_data ORDER BY timestamp")
    result = cursor.fetchall()
    connection.close()
    timestamps = []
    samples = []
    for row in result:
        timestamps.append(row[0])
        samples.append(row[1])
    return timestamps, samples

def load_co2_samples():
    connection = sqlite3.connect('iot_hub.db')
    cursor = connection.cursor()
    cursor.execute("SELECT timestamp, eco2 FROM aiq_data ORDER BY timestamp")
    result = cursor.fetchall()
    connection.close()
    timestamps = []
    samples = []
    for row in result:
        timestamps.append(row[0])
        samples.append(row[1])
    return timestamps, samples

def load_last_aiq_sample():
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
    timestamp, temperature, humidity = load_last_environmental_sample()
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

@app.route("/get_last_environmental_sample")
def get_last_environmental_sample():
    timestamp, temperature, humidity = load_last_environmental_sample()
    if timestamp and temperature and humidity:
        data = {
            'timestamp': timestamp,
            'temperature': temperature,
            'humidity': humidity
        }
        return jsonify(data)

@app.route("/aiq")
def aiq():
    timestamp, tvoc, eco2 = load_last_aiq_sample()
    if timestamp and tvoc and eco2:
        template_data = {
            'timestamp': timestamp,
            'tvoc': tvoc,
            'eco2': eco2
        }
        return render_template('aiq.html', **template_data)
    template_data = {
        'description': 'air quality'
    }
    return render_template('nodata.html', **template_data)

@app.route("/get_last_aiq_sample")
def get_last_aiq_sample():
    timestamp, tvoc, eco2 = load_last_aiq_sample()
    if timestamp and tvoc and eco2:
        data = {
            'timestamp': timestamp,
            'tvoc': tvoc,
            'eco2': eco2
        }
        return jsonify(data)

@app.route('/plot_temperature')
def plot_temperature():
    timestamps, samples = load_temperature_samples()
    ys = samples
    figure = Figure()
    axis = figure.add_subplot(1, 1, 1)
    axis.set_title("Temperature [°C]")
    axis.set_xlabel("Samples")
    axis.grid(True)
    xs = range(len(timestamps))
    axis.plot(xs, ys)
    canvas = FigureCanvas(figure)
    output = io.BytesIO()
    canvas.print_png(output)
    response = make_response(output.getvalue())
    response.mimetype = 'image/png'
    return response

@app.route('/plot_humidity')
def plot_humidity():
    timestamps, samples = load_humidity_samples()
    ys = samples
    figure = Figure()
    axis = figure.add_subplot(1, 1, 1)
    axis.set_title("Humidity [%]")
    axis.set_xlabel("Samples")
    axis.grid(True)
    xs = range(len(timestamps))
    axis.plot(xs, ys)
    canvas = FigureCanvas(figure)
    output = io.BytesIO()
    canvas.print_png(output)
    response = make_response(output.getvalue())
    response.mimetype = 'image/png'
    return response

@app.route('/plot_tvoc')
def plot_tvoc():
    timestamps, samples = load_tvoc_samples()
    ys = samples
    figure = Figure()
    axis = figure.add_subplot(1, 1, 1)
    axis.set_title("TVOC [PPB]")
    axis.set_xlabel("Samples")
    axis.grid(True)
    xs = range(len(timestamps))
    axis.plot(xs, ys)
    canvas = FigureCanvas(figure)
    output = io.BytesIO()
    canvas.print_png(output)
    response = make_response(output.getvalue())
    response.mimetype = 'image/png'
    return response

@app.route('/plot_co2')
def plot_co2():
    timestamps, samples = load_co2_samples()
    ys = samples
    figure = Figure()
    axis = figure.add_subplot(1, 1, 1)
    axis.set_title("eCO2 [PPM]")
    axis.set_xlabel("Samples")
    axis.grid(True)
    xs = range(len(timestamps))
    axis.plot(xs, ys)
    canvas = FigureCanvas(figure)
    output = io.BytesIO()
    canvas.print_png(output)
    response = make_response(output.getvalue())
    response.mimetype = 'image/png'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)