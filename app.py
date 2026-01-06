
from flask import Flask, render_template, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
import pymysql

app = Flask(__name__)
app.secret_key = 'ehr_secret_key'

# Initialize Bcrypt for password security
bcrypt = Bcrypt(app)

# Updated Database Connection Function
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='SAJANA123*', # <--- CHANGE THIS to your MySQL password
        database='ehr_system',
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def home():

    # This now shows the layout's home state
    return render_template('layout.html')

@app.route('/about')
def about():
    # This shows the About Us page
    return render_template('about.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Capture the data from the HTML form fields
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 2. Scramble the password for security
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # 3. Connect to MySQL and save the data
        try:
            conn = get_db_connection() # Using the connection function we made earlier
            cur = conn.cursor()
            
            # The SQL command to "Insert" the new doctor
            cur.execute("INSERT INTO doctors (username, email, password) VALUES (%s, %s, %s)", 
                        (username, email, hashed_pw))
            
            conn.commit() # This "saves" the changes to the database
            cur.close()
            conn.close()
            
            # If successful, send them to the login page
            return redirect(url_for('login'))
            
        except Exception as e:
            # This will show an error if the username is already taken
            return f"Registration Error: {e}"
            
    # If the user is just visiting the page (GET), show the form
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password_candidate = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Look for the doctor in the database
        cur.execute("SELECT * FROM doctors WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            # Check if the password is correct (compares hashed version)
            if bcrypt.check_password_hash(user['password'], password_candidate):
                # SUCCESS: Create a "Session" (Digital ID Badge)
                session['logged_in'] = True
                session['doctor_id'] = user['id']
                session['username'] = user['username']
                
                return redirect(url_for('dashboard')) # Go to Dashboard
            else:
                return "<h1>Invalid Password</h1>"
        else:
            return "<h1>User not found</h1>"

    return render_template('login.html')
    
@app.route('/dashboard')
def dashboard():
    if 'logged_in' in session:
        return f"<h1>Welcome Dr. {session['username']}! This is your private Dashboard.</h1>"
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear() # Deletes the digital ID badge
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)


