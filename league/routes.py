from flask import render_template
from league import app

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

@app.route("/login")
def login():
    pass

@app.route("/logout")
def logout():
    pass

@app.route("/register")
def register():
    pass

