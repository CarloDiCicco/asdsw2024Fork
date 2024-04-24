from flask import Flask

app = Flask(__name__)

# definisco la rotta di riferimento standard
@app.route('/')
def hello():
    return 'Hello, World!\n'

# definisco una nuova rotta "/ita"
@app.route('/ita')
def hello_ita():
    return 'Ciao a tutti!\n'

@app.route('/deu')
def hello_deu():
    return 'Hallo Welt\n'
