# app.py
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "这是我的第一个 MVP！🚀"

if __name__ == "__main__":
    app.run(debug=True)
