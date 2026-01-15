import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
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

@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/home')
def home():
    return render_template('home.html')
    


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

@app.route('/profile')
def profile():
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT * FROM doctors WHERE id = %s", (session['doctor_id'],))
    doctor = cur.fetchone()
    db.close()
    
    return render_template('profile.html', doctor=doctor)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # Update Doctor Info (Personal Details Only)
    query = """UPDATE doctors SET first_name=%s, last_name=%s, category=%s WHERE id=%s"""
    cur.execute(query, (
        request.form['first_name'],
        request.form['last_name'],
        request.form['category'],
        session['doctor_id']
    ))
    db.commit()
    db.close()
    
    flash("Personal details updated successfully!", "success")
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for('profile'))
        
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT password FROM doctors WHERE id = %s", (session['doctor_id'],))
    doctor = cur.fetchone()
    
    if doctor and bcrypt.check_password_hash(doctor['password'], current_password):
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        cur.execute("UPDATE doctors SET password = %s WHERE id = %s", (hashed_password, session['doctor_id']))
        db.commit()
        flash("Password changed successfully!", "success")
    else:
        flash("Incorrect current password.", "danger")
        
    db.close()
    return redirect(url_for('profile'))

@app.route('/request_email_change', methods=['POST'])
def request_email_change():
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    new_email = request.form.get('new_email')
    if not new_email:
        flash("Please enter a valid email.", "danger")
        return redirect(url_for('profile'))
        
    # Generate Token
    token = serializer.dumps(new_email, salt='email-change-salt')
    
    # Send Email
    try:
        confirm_url = url_for('confirm_new_email', token=token, _external=True)
        msg = Message('Confirm New Email Address - City General Hospital', 
                      sender=app.config['MAIL_USERNAME'], 
                      recipients=[new_email])
        msg.body = f"""Please confirm your new email address by clicking the link below:
        
{confirm_url}

If you did not request this change, please ignore this email.
"""
        mail.send(msg)
        flash(f"Confirmation email sent to {new_email}. Please check your inbox.", "info")
    except Exception as e:
        print(f"Email failed: {e}")
        flash("Failed to send confirmation email. Please try again.", "danger")
        
    return redirect(url_for('profile'))

@app.route('/confirm_new_email/<token>')
def confirm_new_email(token):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    try:
        new_email = serializer.loads(token, salt='email-change-salt', max_age=3600)
    except SignatureExpired:
        flash("The confirmation link has expired.", "danger")
        return redirect(url_for('profile'))
    except Exception:
        flash("Invalid confirmation link.", "danger")
        return redirect(url_for('profile'))
        
    # Update Email
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("UPDATE doctors SET email = %s WHERE id = %s", (new_email, session['doctor_id']))
        db.commit()
        flash("Email address updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating email: {e}", "danger")
    finally:
        db.close()
        
    return redirect(url_for('profile'))

# --- PATIENT ROUTES (CRUD) ---

@app.route('/patient/<int:id>')
def patient_details(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    db = get_db_connection()
    cur = db.cursor()
    
    # 1. Fetch Patient
    cur.execute("SELECT * FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    patient = cur.fetchone()
    
    if not patient:
        db.close()
        flash("Patient not found or access denied.", "danger")
        return redirect(url_for('dashboard'))

    # Mark as seen if new
    if patient['is_seen'] == 0:
        cur.execute("UPDATE patients SET is_seen = 1 WHERE id = %s", (id,))
        db.commit()

    # 2. Fetch History (Appointments)
    cur.execute("""
        SELECT * FROM appointments 
        WHERE patient_id = %s 
        ORDER BY appointment_date DESC, appointment_time DESC
    """, (id,))
    history = cur.fetchall()

    # 3. Fetch Documents and Attach to Visits (by Date)
    cur.execute("SELECT * FROM documents WHERE patient_id = %s", (id,))
    all_docs = cur.fetchall()
    
    # Helper to attach docs
    for visit in history:
        visit['documents'] = []
        visit_date = str(visit['appointment_date']) # Ensure string comparison
        for doc in all_docs:
            doc_date = str(doc['document_date'])
            if doc_date == visit_date:
                visit['documents'].append(doc)

    db.close()
    return render_template('patient_details.html', patient=patient, history=history)

@app.route('/patient_details/<int:id>')
def patient_profile_view(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # 1. Fetch Basic Patient Info
    cur.execute("SELECT * FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    patient = cur.fetchone()
    
    if not patient:
        db.close()
        flash("Patient not found.", "danger")
        return redirect(url_for('dashboard'))

    # 2. Fetch Attached Documents (for downloads)
    cur.execute("SELECT * FROM documents WHERE patient_id = %s ORDER BY created_at DESC", (id,))
    documents = cur.fetchall()

    # 3. Fetch Appointment History
    cur.execute("SELECT * FROM appointments WHERE patient_id = %s AND doctor_id = %s ORDER BY appointment_date DESC", (id, session['doctor_id']))
    history = cur.fetchall()
    
    # 4. Map Documents to Visits (by Date) - Basic Strategy
    # Iterate history and find docs with matching date
    for visit in history:
        visit['documents'] = []
        
        # FIX: Convert timedelta to string for JSON serialization
        if visit.get('appointment_time'):
            if isinstance(visit['appointment_time'], timedelta):
                 total_seconds = int(visit['appointment_time'].total_seconds())
                 hours = total_seconds // 3600
                 minutes = (total_seconds % 3600) // 60
                 visit['appointment_time'] = f"{hours:02}:{minutes:02}"
            else:
                 visit['appointment_time'] = str(visit['appointment_time'])

        if visit['appointment_date']:
            # Depending on type (date vs string), ensure comparison works.
            # PyMySQL returns date object.
            v_date = visit['appointment_date']
            for doc in documents:
                if doc['document_date'] == v_date:
                    visit['documents'].append(doc)
    
    db.close()
    
    return render_template('patient_details.html', patient=patient, history=history)

@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # POST: Update Clinical Encounter (Vitals, Diagnosis, etc.)
    if request.method == 'POST':
        appt_id = request.form.get('appointment_id')
        if appt_id:
            try:
                # Update Vitals & Clinical Data
                update_query = """UPDATE appointments SET 
                                  blood_pressure=%s, temperature=%s, pulse_rate=%s, sp_o2=%s,
                                  weight=%s, final_diagnosis=%s, clinical_notes=%s, prescription=%s, status='Completed' 
                                  WHERE id=%s AND doctor_id=%s"""
                params = (
                    request.form.get('blood_pressure'),
                    request.form.get('temperature') or None,
                    request.form.get('pulse_rate') or None,
                    request.form.get('sp_o2') or None,
                    request.form.get('weight') or None,
                    request.form.get('final_diagnosis'),
                    request.form.get('clinical_notes'),
                    request.form.get('prescription'),
                    appt_id,
                    session['doctor_id']
                )
                cur.execute(update_query, params)

                # Handle Documents
                files = request.files.getlist('medical_docs')
                if files:
                    # Fetch patient_id for this appt
                    cur.execute("SELECT patient_id, appointment_date FROM appointments WHERE id=%s", (appt_id,))
                    appt = cur.fetchone()
                    if appt:
                        ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
                        for f in files:
                            if f and f.filename:
                                ext = f.filename.rsplit('.', 1)[1].lower() if '.' in f.filename else ''
                                if ext in ALLOWED_EXTENSIONS:
                                    fname = secure_filename(f.filename)
                                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                                    doc_query = """INSERT INTO documents (patient_id, doctor_id, file_path, document_date) 
                                                   VALUES (%s, %s, %s, %s)"""
                                    cur.execute(doc_query, (appt['patient_id'], session['doctor_id'], fname, appt['appointment_date']))
                                else:
                                    flash(f"Skipped invalid file: {f.filename} (Allowed: PDF, JPG, PNG)", "warning")

                db.commit()
                flash("Encounter finalized and saved.", "success")
            except Exception as e:
                flash(f"Error saving encounter: {e}", "danger")
        
        db.close()
        return redirect(url_for('appointments'))

    # GET: Fetch Today's Appointments with Patient Details
    query_today = """
        SELECT a.*, p.first_name, p.last_name, p.insurance_number, p.gender, p.age 
        FROM appointments a 
        JOIN patients p ON a.patient_id = p.id 
        WHERE a.doctor_id = %s AND a.appointment_date = CURDATE() 
        ORDER BY a.appointment_time ASC
    """
    cur.execute(query_today, (session['doctor_id'],))
    today_appts = cur.fetchall()
    
    db.close()
    
    # Format time for display (remove seconds if needed, or handle in template)
    for appt in today_appts:
        if appt['appointment_time']:
            # Ensure it's string format H:M
            if isinstance(appt['appointment_time'], (timedelta,)): 
                 # PyMySQL might return timedelta for TIME columns
                 total_seconds = int(appt['appointment_time'].total_seconds())
                 hours = total_seconds // 3600
                 minutes = (total_seconds % 3600) // 60
                 appt['appointment_time'] = f"{hours:02}:{minutes:02}"
            else:
                 # If it's already string or time object, just check format. 
                 # Assuming PyMySQL returns timedelta for TIME type usually.
                 pass

    return render_template('appointments.html', today_appts=today_appts, get_today_date=datetime.now().strftime('%Y-%m-%d'))

# --- BOOKING WORKFLOW ---

@app.route('/search_patient_api')
def search_patient_api():
    if 'logged_in' not in session: return jsonify([])
    
    query = request.args.get('q', '')
    if not query: return jsonify([])
    
    db = get_db_connection()
    cur = db.cursor()
    # Search by name or insurance number
    q_str = f"%{query}%"
    cur.execute("SELECT id, first_name, last_name, insurance_number, age FROM patients WHERE doctor_id = %s AND (first_name LIKE %s OR last_name LIKE %s OR insurance_number LIKE %s) LIMIT 5", 
               (session['doctor_id'], q_str, q_str, q_str))
    results = cur.fetchall()
    db.close()
    return jsonify(results)

@app.route('/api/all_appointments')
def all_appointments_api():
    if 'logged_in' not in session: return jsonify([])
    
    db = get_db_connection()
    cur = db.cursor()
    # Fetch appointments for calendar
    cur.execute("""
        SELECT a.appointment_date, a.appointment_time, p.first_name 
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = %s
    """, (session['doctor_id'],))
    appts = cur.fetchall()
    db.close()
    
    events = []
    for a in appts:
        if a['appointment_date'] and a['appointment_time']:
            # FIX: Explicitly convert timedelta to string to avoid JSON errors
            time_val = a['appointment_time']
            if isinstance(time_val, timedelta):
                # Format as HH:MM:SS
                total_seconds = int(time_val.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                time_str = str(time_val)

            # Combine Date and Time into ISO string
            start_datetime = f"{a['appointment_date']}T{time_str}"
            events.append({
                "title": a['first_name'],
                "start": start_datetime
            })
            
    return jsonify(events)

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        appt_date = request.form.get('appointment_date')
        appt_time = request.form.get('appointment_time')
        reason = request.form.get('reason_for_visit')
        
        db = get_db_connection()
        cur = db.cursor()
        
        try:
            # 1. Insert Appointment (Scheduled)
            query = """INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason_for_visit) 
                       VALUES (%s, %s, %s, %s, 'Scheduled', %s)"""
            cur.execute(query, (patient_id, session['doctor_id'], appt_date, appt_time, reason))
            
            # 2. Fetch Patient Email for Notification
            cur.execute("SELECT email, first_name, last_name FROM patients WHERE id = %s", (patient_id,))
            patient = cur.fetchone()
            
            db.commit()
            
            # 3. Send Email
            if patient and patient['email']:
                try:
                    msg = Message('Appointment Confirmation - City General Hospital', 
                                sender=app.config['MAIL_USERNAME'], 
                                recipients=[patient['email']])
                    msg.body = f"""Dear {patient['first_name']} {patient['last_name']},
                    
Your appointment is confirmed.
Date: {appt_date}
Time: {appt_time}
Reason: {reason}

Please arrive 15 minutes early.
"""
                    mail.send(msg)
                    flash("Appointment scheduled successfully! Confirmation email sent.", "success")
                except Exception as e:
                    print(f"Email failed: {e}")
                    flash("Appointment saved, but email failed. Please notify patient manually.", "warning")
            else:
                flash("Appointment scheduled successfully (No email on file).", "success")
        except Exception as e:
            flash(f"Error booking appointment: {e}", "danger")
        finally:
            db.close()
            
        return redirect(url_for('book_appointment'))

    # GET: Fetch all future appointments for management table
    db = get_db_connection()
    cur = db.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    query = """
        SELECT a.id, a.appointment_date, a.appointment_time, a.status, a.reason_for_visit,
               p.first_name, p.last_name, p.insurance_number
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = %s AND a.appointment_date >= %s
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
    """
    cur.execute(query, (session['doctor_id'], today))
    appointments = cur.fetchall()
    db.close()

    return render_template('book_appointment.html', get_today_date=today, appointments=appointments)

@app.route('/update_appointment_details/<int:id>', methods=['POST'])
def update_appointment_details(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    new_date = request.form.get('appointment_date')
    new_time = request.form.get('appointment_time')
    new_reason = request.form.get('reason_for_visit')
    
    db = get_db_connection()
    cur = db.cursor()
    
    # Verify ownership
    cur.execute("SELECT id FROM appointments WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    if cur.fetchone():
        try:
            cur.execute("UPDATE appointments SET appointment_date = %s, appointment_time = %s, reason_for_visit = %s WHERE id = %s", 
                       (new_date, new_time, new_reason, id))
            db.commit()
            flash("Appointment details updated.", "success")
        except Exception as e:
            flash(f"Error updating appointment: {e}", "danger")
    else:
        flash("Access denied or appointment not found.", "danger")
        
    db.close()
    return redirect(url_for('book_appointment'))

@app.route('/delete_booking/<int:id>')
def delete_booking(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # Verify ownership
    cur.execute("SELECT id FROM appointments WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    if cur.fetchone():
        try:
            cur.execute("DELETE FROM appointments WHERE id = %s", (id,))
            db.commit()
            flash("Appointment cancelled and removed.", "warning")
        except Exception as e:
            flash(f"Error deleting appointment: {e}", "danger")
    else:
        flash("Access denied or appointment not found.", "danger")
        
    db.close()
    return redirect(url_for('book_appointment'))

    return render_template('book_appointment.html', get_today_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/encounter/<int:id>', methods=['GET', 'POST'])
def encounter(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # Verify appointment ownership and fetch data
    cur.execute("SELECT * FROM appointments WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    appt = cur.fetchone()
    
    if not appt:
        db.close()
        flash("Appointment not found.", "danger")
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        # Update Appointment
        final_diag = request.form.get('final_diagnosis')
        notes = request.form.get('clinical_notes')
        presc = request.form.get('prescription')
        weight = request.form.get('weight')
        temp = request.form.get('temperature')
        
        # Append temp to notes if provided (since no DB col)
        if temp:
            notes = f"Temp: {temp}°C\n{notes}"
            
        update_query = """UPDATE appointments SET 
                          weight=%s, final_diagnosis=%s, clinical_notes=%s, prescription=%s, status='Completed' 
                          WHERE id=%s"""
        cur.execute(update_query, (weight, final_diag, notes, presc, id))
        
        # Handle Documents
        files = request.files.getlist('medical_docs')
        if files:
            for f in files:
                if f and f.filename:
                    fname = secure_filename(f.filename)
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                    # Link to patient (via appt.patient_id) and date (appt.appointment_date or today?)
                    # Usually linked to Visit Date.
                    doc_query = """INSERT INTO documents (patient_id, doctor_id, file_path, document_date) 
                                   VALUES (%s, %s, %s, %s)"""
                    cur.execute(doc_query, (appt['patient_id'], session['doctor_id'], fname, appt['appointment_date']))
        
        db.commit()
        db.close()
        flash("Visit finalized and saved.", "success")
        return redirect(url_for('dashboard'))

    # GET: Fetch Patient for Header
    cur.execute("SELECT * FROM patients WHERE id = %s", (appt['patient_id'],))
    patient = cur.fetchone()
    db.close()
    
    return render_template('encounter.html', appointment=appt, patient=patient, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/delete_appointment/<int:id>')
def delete_appointment(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    db = get_db_connection()
    cur = db.cursor()
    
    # Verify ownership before deleting
    cur.execute("SELECT patient_id FROM appointments WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    appt = cur.fetchone()
    
    if appt:
        cur.execute("DELETE FROM appointments WHERE id = %s", (id,))
        # Also delete linked documents? User didn't specify, but usually good.
        # But documents table links to patient_id + document_date, not appointment_id directly.
        # So we leave them or delete manually. I'll leave them to avoid accidental data loss.
        db.commit()
        flash("Visit deleted.", "warning")
        return redirect(url_for('patient_profile_view', id=appt['patient_id']))
    
    db.close()
    flash("Appointment not found or access denied.", "danger")
    return redirect(url_for('dashboard'))
@app.route('/edit_patient/<int:id>', methods=['GET'])
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
                      first_name=%s, last_name=%s, insurance_number=%s, age=%s, 
                      gender=%s, has_allergies=%s, created_at=%s,
                      email=%s, phone=%s, address=%s
                      WHERE id=%s"""
    
    # Handle created_at override if provided, else keep existing?
    # Usually we don't update Registration Date unless necessary. 
    # But user asked for "editing of... Registration Date".
    # Ensure form sends `created_at`.
    
    cur.execute(update_query, (
        request.form.get('first_name'), request.form.get('last_name'), request.form.get('insurance_number'),
        request.form.get('age'), request.form.get('gender'),
        'Yes' if request.form.get('allergies') else 'No',
        request.form.get('created_at'),
        request.form.get('email'), request.form.get('phone'), request.form.get('address'),
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

@app.route('/toggle_status/<int:id>', methods=['POST'])
def toggle_status(id):
    if 'logged_in' not in session: return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    db = get_db_connection()
    cur = db.cursor()
    
    # Check ownership
    cur.execute("SELECT id, is_active FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
    patient = cur.fetchone()
    
    if not patient:
        db.close()
        return jsonify({'success': False, 'message': 'Patient not found'}), 404
    
    # Toggle status
    new_status = 0 if patient['is_active'] else 1
    cur.execute("UPDATE patients SET is_active = %s WHERE id = %s", (new_status, id))
    db.commit()
    db.close()
    
    flash("Patient status updated.", "info")
    return redirect(url_for('patient_details', id=id))

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

    # 1. Active Patients
    cur.execute("SELECT COUNT(*) as count FROM patients WHERE doctor_id = %s AND is_active = 1", (session['doctor_id'],))
    active_count = cur.fetchone()['count']

    # 2. Total Patients treated
    cur.execute("SELECT COUNT(*) as count FROM patients WHERE doctor_id = %s", (session['doctor_id'],))
    total_count = cur.fetchone()['count']

    # 3. Today's Appointments
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) as count FROM appointments WHERE doctor_id = %s AND appointment_date = %s", (session['doctor_id'], today))
    today_count = cur.fetchone()['count']

    db.close()
    return render_template('dashboard.html', patients=patients, active_count=active_count, total_count=total_count, today_count=today_count)

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
        
        # 2. Insert Patient Data (Static Demographics ONLY)
        # Registration Date (created_at) is handled by DB default or passed if manual date needed?
        # Form has 'created_at'. Let's use it if populated, else DB default. 
        # But DB schema: created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP.
        # If I want to override, I should include it in INSERT.
        # Field name in form: created_at
        
        reg_date = request.form.get('created_at')
        
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Handle Allergies (List to Comma-String)
        allergy_list = request.form.getlist('allergies')
        other_allergy = request.form.get('other_allergy')
        
        if other_allergy and other_allergy.strip():
            allergy_list.append(other_allergy.strip())
            
        # If list is empty -> 'No', else join into string "Penicillin, Peanuts"
        has_allergies = ", ".join(allergy_list) if allergy_list else 'No'
        
        if reg_date:
            query = """INSERT INTO patients (doctor_id, first_name, last_name, insurance_number, 
                       gender, age, has_allergies, image_path, created_at, email, phone, address, medical_history, is_seen) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)"""
            params = (
                session['doctor_id'], 
                request.form.get('first_name'), 
                request.form.get('last_name'),
                request.form.get('insurance_number'), 
                request.form.get('gender'),
                request.form.get('age'),
                has_allergies, 
                filename,
                reg_date,
                email, phone, address,
                request.form.get('medical_history')
            )
        else:
            query = """INSERT INTO patients (doctor_id, first_name, last_name, insurance_number, 
                       gender, age, has_allergies, image_path, email, phone, address, medical_history, is_seen) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)"""
            params = (
                session['doctor_id'], 
                request.form.get('first_name'), 
                request.form.get('last_name'),
                request.form.get('insurance_number'), 
                request.form.get('gender'),
                request.form.get('age'),
                has_allergies, 
                filename,
                email, phone, address,
                request.form.get('medical_history')
            )
            
        cur.execute(query, params)
        db.commit()
        db.close()
        
        flash("Patient registered successfully! You can now add an appointment.", "success")
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