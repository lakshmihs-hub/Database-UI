from flask import Flask, render_template

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/creation')
def creation():
    return render_template('creation.html')

@app.route('/fallout')
def fallout():
    return render_template('fallout.html')

@app.route('/migration')
def migration():
    return render_template('migration.html')

@app.errorhandler(404)
def notfound(e):
    return render_template('notfound.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
