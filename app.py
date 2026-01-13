import os
from datetime import datetime, timedelta
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
def index():
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # Total Patients
    cur.execute("SELECT COUNT(*) as count FROM patients WHERE doctor_id = %s", (session['doctor_id'],))
    total_patients = cur.fetchone()['count']
    
    # Gender Stats
    cur.execute("SELECT gender, COUNT(*) as count FROM patients WHERE doctor_id = %s GROUP BY gender", (session['doctor_id'],))
    gender_stats = cur.fetchall()

    # Today's Appointments
    today = datetime.now().date()
    cur.execute("SELECT first_name, last_name, id, image_path FROM patients WHERE doctor_id = %s AND appointment_date = %s", (session['doctor_id'], today))
    today_appts = cur.fetchall()

    # Tomorrow's Appointments
    tomorrow = today + timedelta(days=1)
    cur.execute("SELECT first_name, last_name, id, image_path FROM patients WHERE doctor_id = %s AND appointment_date = %s", (session['doctor_id'], tomorrow))
    tomorrow_appts = cur.fetchall()
    
    db.close()
    
    return render_template('home.html', total_patients=total_patients, gender_stats=gender_stats, today_appts=today_appts, tomorrow_appts=tomorrow_appts)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.form['password'] != request.form['confirm_password']:
            flash("Passwords do not match!", "danger")
            return render_template('register.html')
            
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

@app.route('/patient/<int:id>')
def patient_details(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    db = get_db_connection()
    cur = db.cursor()
    # Fetch patient
    cur.execute("SELECT * FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    patient = cur.fetchone()
    
    # Mark as seen if new
    if patient and patient['is_seen'] == 0:
        cur.execute("UPDATE patients SET is_seen = 1 WHERE id = %s", (id,))
        db.commit()
        
    db.close()
    
    if not patient:
        flash("Patient not found or access denied.", "danger")
        return redirect(url_for('dashboard'))
        
    return render_template('patient_details.html', patient=patient)

@app.route('/edit_patient/<int:id>')
def edit_patient(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    db = get_db_connection()
    cur = db.cursor()
    
    # Fetch patient
    cur.execute("SELECT * FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    patient = cur.fetchone()
    
    # Fetch documents for this patient
    cur.execute("SELECT * FROM documents WHERE patient_id = %s ORDER BY created_at DESC", (id,))
    documents = cur.fetchall()
    
    db.close()
    
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for('dashboard'))
        
    return render_template('edit_patient.html', patient=patient, documents=documents)

@app.route('/update_patient/<int:id>', methods=['POST'])
def update_patient(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # Check ownership
    cur.execute("SELECT id FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    if not cur.fetchone():
        db.close()
        flash("Access Denied.", "danger")
        return redirect(url_for('dashboard'))
    
    # 1. Update Basic Info
    update_query = """UPDATE patients SET 
                      first_name=%s, last_name=%s, insurance_number=%s, age=%s, weight=%s, 
                      gender=%s, appointment_date=%s, has_allergies=%s, medical_history=%s 
                      WHERE id=%s"""
    
    cur.execute(update_query, (
        request.form.get('first_name'), request.form.get('last_name'), request.form.get('insurance_number'),
        request.form.get('age'), request.form.get('weight'), request.form.get('gender'),
        request.form.get('appt_date') or None,
        'Yes' if request.form.get('allergies') else 'No',
        request.form.get('history'),
        id
    ))
    
    # 2. Handle Profile Image Update
    file = request.files.get('patient_img')
    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cur.execute("UPDATE patients SET image_path=%s WHERE id=%s", (filename, id))
        
    # 3. Handle New Medical Documents
    files = request.files.getlist('medical_docs')
    doc_dates = request.form.getlist('doc_date') # Note: edit_patient uses 'doc_date' (singular/flat?) or list?
    # Checking edit_patient.html: <input name="doc_date"> is singular but inside loop? No, it's one row. 
    # But wait, edit_patient.html allows multiple uploads?
    # Line 111: multiple input. Line 114: one date input. 
    # So all files get the same date.
    
    d_date = request.form.get('doc_date')
    
    if files:
        for f in files:
            if f and f.filename:
                fname = secure_filename(f.filename)
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                cur.execute("INSERT INTO documents (patient_id, doctor_id, file_path, document_date) VALUES (%s, %s, %s, %s)", 
                            (id, session['doctor_id'], fname, d_date or None))

    db.commit()
    db.close()
    flash("Patient updated successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/patient/<int:id>/radiology')
def radiology_gallery(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    db = get_db_connection()
    cur = db.cursor()
    
    cur.execute("SELECT * FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    patient = cur.fetchone()
    
    if not patient:
        db.close()
        return redirect(url_for('dashboard'))
        
    cur.execute("SELECT * FROM documents WHERE patient_id = %s ORDER BY created_at DESC", (id,))
    documents = cur.fetchall()
    db.close()
    
    return render_template('radiology_gallery.html', patient=patient, documents=documents)

@app.route('/delete_report/<int:doc_id>')
def delete_report(doc_id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    patient_id = request.args.get('patient_id')
    
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("DELETE FROM documents WHERE id = %s AND doctor_id = %s", (doc_id, session['doctor_id']))
    db.commit()
    db.close()
    
    flash("Document deleted.", "info")
    return redirect(url_for('edit_patient', id=patient_id) if patient_id else url_for('dashboard'))

@app.route('/download_report/<int:doc_id>')
def download_report(doc_id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT file_path FROM documents WHERE id = %s", (doc_id,))
    doc = cur.fetchone()
    db.close()
    
    if doc:
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], doc['file_path'], as_attachment=True)
    return "File not found", 404

# --- DASHBOARD & LISTS ---

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session: return redirect(url_for('login'))
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT * FROM patients WHERE doctor_id = %s", (session['doctor_id'],))
    patients = cur.fetchall()
    db.close()
    return render_template('dashboard.html', patients=patients)

@app.route('/overview')
def dashboard_overview():
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # 1. Total Patients
    cur.execute("SELECT COUNT(*) as total FROM patients WHERE doctor_id = %s", (session['doctor_id'],))
    total_patients = cur.fetchone()['total']
    
    # 2. Gender Statistics
    cur.execute("SELECT gender, COUNT(*) as count FROM patients WHERE doctor_id = %s GROUP BY gender", (session['doctor_id'],))
    gender_stats = cur.fetchall()
    
    # 3. Appointment Trends (Last 7 days)
    cur.execute("""SELECT appointment_date, COUNT(*) as count FROM patients 
                   WHERE doctor_id = %s GROUP BY appointment_date 
                   ORDER BY appointment_date ASC LIMIT 7""", (session['doctor_id'],))
    appt_stats = cur.fetchall()
    
    db.close()
    return render_template('dashboard_overview.html', 
                           total_patients=total_patients, 
                           gender_stats=gender_stats, 
                           appt_stats=appt_stats)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'logged_in' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        # 1. Patient Image Handling
        file = request.files.get('patient_img')
        filename = ""
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        db = get_db_connection()
        cur = db.cursor()
        
        # 2. Insert Patient Data (Including new age/weight columns)
        query = """INSERT INTO patients (doctor_id, first_name, last_name, insurance_number, 
                   gender, age, weight, has_allergies, medical_history, appointment_date, image_path, is_seen) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)"""
        
        cur.execute(query, (
            session['doctor_id'], 
            request.form.get('first_name'), 
            request.form.get('last_name'),
            request.form.get('insurance_number'), 
            request.form.get('gender'),
            request.form.get('age'),            # New Field
            request.form.get('weight'),         # New Field
            'Yes' if request.form.get('allergies') else 'No', 
            request.form.get('history'), 
            request.form.get('appt_date') or None, 
            filename
        ))
        patient_id = cur.lastrowid # Get the ID of the new patient
        
        # 3. Handle Medical Document Uploads (Multiple)
        files = request.files.getlist('medical_docs')
        doc_dates = request.form.getlist('doc_dates')
        
        if files:
            for idx, f in enumerate(files):
                if f and f.filename:
                    fname = secure_filename(f.filename)
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    
                    # Try to get corresponding date, else default to today
                    d_date = doc_dates[idx] if idx < len(doc_dates) and doc_dates[idx] else None
                    
                    doc_query = """INSERT INTO documents (patient_id, doctor_id, file_path, document_date) 
                                   VALUES (%s, %s, %s, %s)"""
                    cur.execute(doc_query, (patient_id, session['doctor_id'], fname, d_date))

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