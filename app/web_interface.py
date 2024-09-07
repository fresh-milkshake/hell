from flask import Flask, render_template, jsonify

app = Flask(__name__)
hell_instance = None


@app.route("/")
def index():
    return render_template("index.html", daemons=hell_instance.daemons)


@app.route("/api/daemons")
def get_daemons():
    return jsonify(
        [
            {
                "name": d.name,
                "pid": d.pid,
                "status": "Running" if d.pid != -1 else "Stopped",
            }
            for d in hell_instance.daemons
        ]
    )


@app.route("/api/kill/<daemon_name>")
def kill_daemon(daemon_name):
    success = hell_instance.kill_daemon(daemon_name)
    return jsonify({"success": success})


def run_web_interface(hell):
    global hell_instance
    hell_instance = hell
    app.run(debug=True)
