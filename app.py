import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
import pymysql
from flask import send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'ehr_secret_key'

# Configure Uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

bcrypt = Bcrypt(app)

# Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'KINGsajana*',  
    'database': 'ehr_system',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**db_config)

# --- ROUTES ---

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        f_name = request.form.get('first_name')
        l_name = request.form.get('last_name')
        med_id = request.form.get('doctor_medical_id') 
        cat = request.form.get('category')              
        uname = request.form.get('username')
        email = request.form.get('email')
        pw = request.form.get('password')
        
        hashed_pw = bcrypt.generate_password_hash(pw).decode('utf-8')
        
        db = get_db_connection()
        cursor = db.cursor()
        try:
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
        cur.execute("SELECT * FROM doctors WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and bcrypt.check_password_hash(user['password'], password_candidate):
            session['logged_in'] = True
            session['doctor_id'] = user['id']
            session['username'] = user['username']
            flash(f"Welcome back, Dr. {user['last_name']}", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid login credentials", "danger")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    # Get the search term from the URL (if any)
    search_query = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if search_query:
        # Search by first_name, last_name, or insurance_number
        # Using %s with % around it allows "partial" matches (e.g. 'jo' matches 'John')
        sql = """
            SELECT * FROM patients 
            WHERE doctor_id = %s 
            AND (first_name LIKE %s OR last_name LIKE %s OR insurance_number LIKE %s)
        """
        like_pattern = f"%{search_query}%"
        cur.execute(sql, (session['doctor_id'], like_pattern, like_pattern, like_pattern))
    else:
        # No search? Show all patients for this doctor
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
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        insurance = request.form.get('insurance_number')
        age = request.form.get('age')
        weight = request.form.get('weight')
        gender = request.form.get('gender')
        allergies = request.form.get('allergies') or "No"
        appt_date = request.form.get('appt_date')
        history = request.form.get('history')

        # Handle Profile Photo
        db_img_path = "uploads/default_user.png" 
        if 'patient_img' in request.files:
            file = request.files['patient_img']
            if file and file.filename != '':
                filename = uuid.uuid4().hex + "_" + secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db_img_path = f"uploads/{filename}"

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            query = """INSERT INTO patients 
                       (first_name, last_name, insurance_number, age, weight, gender, allergies, appt_date, medical_history, patient_img, doctor_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cur.execute(query, (first_name, last_name, insurance, age, weight, gender, allergies, appt_date, history, db_img_path, session['doctor_id']))
            new_patient_id = cur.lastrowid

            # Handle MULTIPLE Medical Documents
            # 4. Handle Dynamic Medical Documents
            if 'medical_docs' in request.files:
                docs = request.files.getlist('medical_docs')
                # IMPORTANT: Use getlist because there are multiple date inputs now
                dates = request.form.getlist('doc_dates') 
                
                # zip() pairs File 1 with Date 1, File 2 with Date 2, etc.
                for doc, d_date in zip(docs, dates):
                    if doc and doc.filename != '':
                        doc_filename = uuid.uuid4().hex + "_" + secure_filename(doc.filename)
                        doc.save(os.path.join(app.config['UPLOAD_FOLDER'], doc_filename))
                        
                        # Save the document with its specific date
                        doc_query = "INSERT INTO patient_documents (patient_id, file_path, document_date) VALUES (%s, %s, %s)"
                        cur.execute(doc_query, (new_patient_id, f"uploads/{doc_filename}", d_date))
            
            conn.commit()
            flash("Patient and documents saved successfully!", "success")
            return redirect(url_for('dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
    return render_template('add_patient.html')

@app.route('/delete_patient/<int:id>')
def delete_patient(id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Delete the patient (This also deletes their documents due to ON DELETE CASCADE)
        cur.execute("DELETE FROM patients WHERE id = %s AND doctor_id = %s", (id, session['doctor_id']))
        conn.commit()
        flash("Patient record has been successfully deleted.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting record: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
        
    return redirect(url_for('dashboard'))

@app.route('/patient/<int:patient_id>')
def view_patient(patient_id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
    patient = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('patient_details.html', patient=patient)

@app.route('/patient/<int:patient_id>/radiology')
def view_radiology(patient_id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT first_name, last_name FROM patients WHERE id = %s", (patient_id,))
    patient = cur.fetchone()
    cur.execute("SELECT * FROM patient_documents WHERE patient_id = %s", (patient_id,))
    documents = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('radiology_gallery.html', patient=patient, documents=documents)

@app.route('/edit_patient/<int:id>')
def edit_patient(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Get the Patient's main data
    cur.execute("SELECT * FROM patients WHERE id = %s", (id,))
    patient = cur.fetchone()
    
    # 2. Get all the X-rays/Reports for this specific patient
    cur.execute("SELECT * FROM patient_documents WHERE patient_id = %s", (id,))
    documents = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('edit_patient.html', patient=patient, documents=documents)

@app.route('/update_patient/<int:id>', methods=['POST'])
def update_patient(id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    
    # 1. Collect all text fields
    f_name = request.form.get('first_name')
    l_name = request.form.get('last_name')
    ins = request.form.get('insurance_number')
    age = request.form.get('age')
    weight = request.form.get('weight')
    gender = request.form.get('gender')
    history = request.form.get('history')
    appt = request.form.get('appt_date')
    # Handle checkbox value
    allergies = "Yes" if request.form.get('allergies') else "No"

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 2. Check if a NEW photo was uploaded
        if 'patient_img' in request.files and request.files['patient_img'].filename != '':
            file = request.files['patient_img']
            filename = uuid.uuid4().hex + "_" + secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_path = f"uploads/{filename}"
            
            # Update including the NEW photo path
            query = """UPDATE patients SET first_name=%s, last_name=%s, insurance_number=%s, age=%s, 
                       weight=%s, gender=%s, medical_history=%s, appt_date=%s, allergies=%s, patient_img=%s
                       WHERE id=%s AND doctor_id=%s"""
            cur.execute(query, (f_name, l_name, ins, age, weight, gender, history, appt, allergies, new_path, id, session['doctor_id']))
        else:
            # Update everything EXCEPT the photo
            query = """UPDATE patients SET first_name=%s, last_name=%s, insurance_number=%s, age=%s, 
                       weight=%s, gender=%s, medical_history=%s, appt_date=%s, allergies=%s
                       WHERE id=%s AND doctor_id=%s"""
            cur.execute(query, (f_name, l_name, ins, age, weight, gender, history, appt, allergies, id, session['doctor_id']))

        conn.commit()
        flash("Medical record successfully synchronized.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    finally:
        cur.close()
        conn.close()
        
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/delete_report/<int:doc_id>')
def delete_report(doc_id):
    patient_id = request.args.get('patient_id')
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Delete the record from the documents table
    cur.execute("DELETE FROM patient_documents WHERE id = %s", (doc_id,))
    
    conn.commit()
    cur.close()
    conn.close()
    
    flash("Report removed.", "info")
    return redirect(url_for('edit_patient', id=patient_id))

@app.route('/download_report/<int:doc_id>')
def download_report(doc_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get the file path from the database
    cur.execute("SELECT file_path FROM patient_documents WHERE id = %s", (doc_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        # result['file_path'] looks like "uploads/filename.jpg"
        # We need to split the folder name from the actual filename
        folder = os.path.join(app.root_path, 'static', 'uploads')
        filename = result['file_path'].split('/')[-1]
        
        return send_from_directory(folder, filename, as_attachment=True)
    
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True)