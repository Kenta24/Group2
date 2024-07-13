import os
import io
from flask import Flask, request, render_template, jsonify
from PIL import Image
import base64
from image_to_sound import ImageToSound

app = Flask(__name__)
its = ImageToSound(ip="10.103.103.47", start_port=8000)

@app.route('/upload_canvas', methods=['POST'])
def upload_canvas():
    data = request.get_json()
    image_data = base64.b64decode(data['image'].split(',')[1])
    image = Image.open(io.BytesIO(image_data))
    image.save('uploaded_image.png')

    parameters = its.process_new_image('uploaded_image.png')
    if parameters:
        print(f"Sent OSC messages with parameters:", parameters)

    return 'Image received and processed', 200

@app.route('/button-clicked', methods=['POST'])
def button_clicked():
    data = request.get_json()
    if data.get('clicked'):
        print("Button was clicked! Resetting ports and sending zero parameters.")
        its.reset_ports_and_send_zero()
        response = {'status': 'success', 'message': 'Button click received and reset performed'}
    else:
        response = {'status': 'error', 'message': 'Invalid request'}

    return jsonify(response)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    its.reset_ports_and_send_zero()  # サーバー起動時にポートをリセットして0パラメータを送信
    app.run(debug=True, host='0.0.0.0', port=5000)  # すべてのネットワークインターフェースでリクエストを受け入れるように設定
