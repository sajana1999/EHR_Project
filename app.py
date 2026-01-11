import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import pymysql
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'ehr_secret_key'

# --- CONFIGURATIONS ---
bcrypt = Bcrypt(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# Database Connection
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root*', # Ensure this matches your MySQL Workbench password
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

# Email Setup
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'chameesharavindu@gmail.com'
app.config['MAIL_PASSWORD'] = 'tkyyujagsspmrlzp' 
mail = Mail(app)

# Image Upload Settings
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    return pymysql.connect(**db_config)

# --- DOCTOR ROUTES (Auth & Verification) ---

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        hashed_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        
        db = get_db_connection()
        cur = db.cursor()
        try:
            # Set is_verified = 0 (False) on creation [Requirement]
            query = """INSERT INTO doctors (first_name, last_name, doctor_medical_id, category, username, email, password, is_verified) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, 0)"""
            cur.execute(query, (
                request.form['first_name'], request.form['last_name'], 
                request.form['doctor_medical_id'], request.form['category'],
                request.form['username'], email, hashed_pw
            ))
            db.commit()

            # Generate confirmation token and send email [Requirement]
            token = serializer.dumps(email, salt='email-confirm-salt')
            link = url_for('confirm_email', token=token, _external=True)
            
            msg = Message('Confirm Your EHR Account', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Welcome! Please click the link to verify your account: {link}"
            mail.send(msg)

            flash("Registration successful! Please check your email to verify your account.", "info")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
        finally:
            db.close()
    return render_template('register.html')

@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        # Decode token [Requirement]
        email = serializer.loads(token, salt='email-confirm-salt', max_age=3600) # 1 hour expiry
    except SignatureExpired:
        return "<h1>The confirmation link has expired.</h1>"
    except:
        return "<h1>Invalid token.</h1>"

    db = get_db_connection()
    cur = db.cursor()
    # Update is_verified = 1 for the corresponding email [Requirement]
    cur.execute("UPDATE doctors SET is_verified = 1 WHERE email = %s", (email,))
    db.commit()
    db.close()

    flash("Email verified! You can now log in.", "success")
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("SELECT * FROM doctors WHERE username = %s", (request.form['username'],))
        user = cur.fetchone()
        db.close()

        if user and bcrypt.check_password_hash(user['password'], request.form['password']):
            # Check if user['is_verified'] is True [Requirement]
            if user['is_verified']:
                session['logged_in'] = True
                session['doctor_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            else:
                # Deny login and flash warning if False [Requirement]
                flash("Your account is not verified. Please check your email for the verification link.", "warning")
                return redirect(url_for('login'))
        
        flash("Invalid username or password", "danger")
    return render_template('login.html')

# --- PATIENT ROUTES (CRUD) ---

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session: return redirect(url_for('login'))
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT * FROM patients WHERE doctor_id = %s", (session['doctor_id'],))
    patients = cur.fetchall()
    db.close()
    return render_template('dashboard.html', patients=patients)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'logged_in' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files.get('patient_img')
        filename = secure_filename(file.filename) if file else ""
        if file: file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        db = get_db_connection()
        cur = db.cursor()
        query = """INSERT INTO patients (doctor_id, first_name, last_name, insurance_number, 
                   gender, has_allergies, medical_history, appointment_date, image_path) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cur.execute(query, (
            session['doctor_id'], request.form['first_name'], request.form['last_name'],
            request.form['insurance_number'], request.form['gender'], 
            'Yes' if request.form.get('allergies') else 'No', 
            request.form['history'], request.form['appt_date'], filename
        ))
        db.commit()
        db.close()
        flash("Patient added successfully!", "success")
        return redirect(url_for('dashboard'))
    return render_template('add_patient.html')

@app.route('/delete_patient/<int:id>')
def delete_patient(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("DELETE FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    db.commit()
    db.close()
    flash("Record deleted.", "warning")
    return redirect(url_for('dashboard'))

# --- FORGOT PASSWORD ---

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email_input = request.form.get('email')
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("SELECT * FROM doctors WHERE email = %s", (email_input,))
        user = cur.fetchone()
        db.close()
        
        if user:
            token = serializer.dumps(email_input, salt='password-reset-salt')
            link = url_for('reset_token', token=token, _external=True)
            msg = Message('Password Reset Request', sender=app.config['MAIL_USERNAME'], recipients=[email_input])
            msg.body = f"To reset your password, visit this link: {link}"
            mail.send(msg)
            flash("A reset link has been sent to your email.", "success")
            return redirect(url_for('login'))
        else:
            flash("Wrong email entered! This email is not registered.", "danger")
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=1800)
    except:
        flash("The reset link is invalid or has expired.", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_pw = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("UPDATE doctors SET password = %s, is_verified = 1 WHERE email = %s", (new_pw, email))
        db.commit()
        db.close()
        flash("Password updated and account verified!", "success")
        return redirect(url_for('login'))
    return render_template('reset_password.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)