import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
import pymysql

from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'ehr_secret_key'

# Configure Uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize Bcrypt for password security
bcrypt = Bcrypt(app)

# Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',  # Ensure this matches your MySQL Workbench password
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**db_config)

# --- ROUTES ---

@app.route('/')
def home():
    # If already logged in, go to dashboard; otherwise, go to login
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Collect data from your enhanced HTML form
        f_name = request.form.get('first_name')
        l_name = request.form.get('last_name')
        med_id = request.form.get('doctor_medical_id') 
        cat = request.form.get('category')             
        uname = request.form.get('username')
        email = request.form.get('email')
        pw = request.form.get('password')
        
        # 2. FIX: Use bcrypt to match your login logic
        hashed_pw = bcrypt.generate_password_hash(pw).decode('utf-8')
        
        db = get_db_connection()
        cursor = db.cursor()
        try:
            # 3. Matches your new enhanced SQL table schema
            query = """INSERT INTO doctors (first_name, last_name, doctor_medical_id, category, username, email, password) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(query, (f_name, l_name, med_id, cat, uname, email, hashed_pw))
            db.commit()
            flash("Doctor account created successfully!", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Database Error: {str(e)}", "danger")
        finally:
            cursor.close()
            db.close()
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password_candidate = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Look for the doctor by username
        cur.execute("SELECT * FROM doctors WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            # FIX: Using bcrypt check
            if bcrypt.check_password_hash(user['password'], password_candidate):
                session['logged_in'] = True
                session['doctor_id'] = user['id']
                session['username'] = user['username']
                session['doctor_name'] = user['first_name']
                flash(f"Welcome back, Dr. {user['last_name']}", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid Password", "danger")
        else:
            flash("User not found", "danger")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    # Requirements: Each doctor views ONLY their own patients
    cur.execute("SELECT * FROM patients WHERE doctor_id = %s", (session['doctor_id'],))
    patients = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('dashboard.html', patients=patients)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        # 1. Get form data
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        insurance = request.form.get('insurance_number')
        age = request.form.get('age')
        weight = request.form.get('weight')
        gender = request.form.get('gender')
        allergies = request.form.get('allergies') or "No" # Checkbox returns 'Yes' or None
        appt_date = request.form.get('appt_date')
        history = request.form.get('history')
        
        # 2. Handle Image Upload
        if 'patient_img' not in request.files:
            flash('No image part', 'danger')
            return redirect(request.url)
            
        file = request.files['patient_img']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Save file with a unique prefix to avoid overwrites
            import uuid
            unique_filename = f"{uuid.uuid4()}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # 3. Save to Database
            conn = get_db_connection()
            cur = conn.cursor()
            try:
                # We need to use dictionary for the image path so we can save relative path
                db_img_path = f"uploads/{unique_filename}"
                
                query = """INSERT INTO patients 
                           (first_name, last_name, insurance_number, age, weight, gender, allergies, appt_date, medical_history, patient_img, doctor_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                
                cur.execute(query, (first_name, last_name, insurance, age, weight, gender, allergies, appt_date, history, db_img_path, session['doctor_id']))
                conn.commit()
                flash("Patient record added successfully!", "success")
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash(f"Error saving patient: {str(e)}", "danger")
            finally:
                cur.close()
                conn.close()
        else:
             flash("Invalid file type. Allowed: png, jpg, jpeg, gif", "danger")

    return render_template('add_patient.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)