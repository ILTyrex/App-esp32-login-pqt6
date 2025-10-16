from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Estado en memoria (simple)
leds = {1: 0, 2: 0, 3: 0}
counter = 0

@app.route('/sendData', methods=['POST'])
def send_data():
    global counter
    data = request.get_json() or {}
    counter = data.get('contador', counter)
    print("Received counter:", counter)
    return jsonify({'status': 'ok'}), 200

@app.route('/getDatos', methods=['GET'])
def get_datos():
    return jsonify({
        'led1': leds[1],
        'led2': leds[2],
        'led3': leds[3],
        'contador': counter
    }), 200

@app.route('/updateLed/<int:id>', methods=['PUT'])
def update_led(id):
    data = request.get_json() or {}
    estado = int(data.get('estado', 0))
    if id in leds:
        leds[id] = 1 if estado else 0
        print(f"Led {id} set to {leds[id]}")
        return jsonify({'status': 'ok'}), 200
    else:
        return jsonify({'error': 'invalid led id'}), 400

if __name__ == '__main__':
    # Ejecutar en la LAN
    app.run(host='0.0.0.0', port=5000)
