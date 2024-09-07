from flask import Flask, render_template, jsonify
from werkzeug.serving import make_server
import threading

app = Flask(__name__)
hell_instance = None
server = None

@app.route('/')
def index():
    return render_template('index.html', daemons=hell_instance.daemons)

@app.route('/api/daemons')
def get_daemons():
    return jsonify([{
        'name': d.name,
        'pid': d.PID,
        'status': 'Running' if d.PID != -1 else 'Stopped'
    } for d in hell_instance.daemons])

@app.route('/api/kill/<daemon_name>')
def kill_daemon(daemon_name):
    success = hell_instance.kill_daemon(daemon_name)
    return jsonify({'success': success})

def run_web_interface(hell):
    global hell_instance, server
    hell_instance = hell
    server = make_server('0.0.0.0', 5000, app)
    server.serve_forever()

def start_web_interface(hell):
    global server
    threading.Thread(target=run_web_interface, args=(hell,), daemon=True).start()

def stop_web_interface():
    global server
    if server:
        server.shutdown()