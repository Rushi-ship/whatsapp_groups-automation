from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from whatsapp_utils import process_recommendations
import time
from dotenv import load_dotenv
import platform
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    try:
        print("Starting file upload process...")
        
        if 'file' not in request.files:
            print("No file part in request")
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        print(f"Received file: {file.filename}")
        
        if file.filename == '':
            print("No selected file")
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            print("Invalid file format")
            return jsonify({'error': 'Invalid file format. Please upload an Excel file'}), 400
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recommendations_{timestamp}.xlsx"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"Saving file to: {filepath}")
        
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Save the file
        file.save(filepath)
        print("File saved successfully")
        
        try:
            # Read and validate the Excel file
            print("Reading Excel file...")
            df = pd.read_excel(filepath)
            
            # Check if this is a generic message upload
            is_generic = request.form.get('type') == 'generic'
            
            if is_generic:
                # For generic messages, only validate group_name column
                if 'group_name' not in df.columns:
                    raise ValueError("Excel file must contain a 'group_name' column")
                # Check for client_name column but don't require it
                has_client_names = 'client_name' in df.columns
                print(f"Client names {'found' if has_client_names else 'not found'} in file")
                if len(df.columns) > 2:
                    print("Warning: Additional columns beyond group_name and client_name will be ignored")
            else:
                # For stock recommendations, validate all required columns
                print(f"Found columns: {df.columns.tolist()}")
                
                required_columns = {
                    'group_name': ['group_name'],
                    'Company': ['Company'],
                    'NSE ticker': ['NSE ticker'],
                    'Reco.': ['Reco.'],
                    'Quantity': ['Quantity'],
                    'Approx. CMP ₹': ['Approx. CMP ₹'],
                    'Value': ['Approx. Value @CMP ₹ Lakh', 'Approx. Value @CMP ₹ Lakhs'],
                    'Order Type': ['Order Type']
                }
                # Add client_name as an optional column
                optional_columns = ['client_name']
                
                missing_columns = []
                for col_key, variations in required_columns.items():
                    if not any(var in df.columns for var in variations):
                        missing_columns.append(col_key)
                
                if missing_columns:
                    print(f"Missing columns: {missing_columns}")
                    os.remove(filepath)
                    return jsonify({'error': f'Missing required columns: {", ".join(missing_columns)}'}), 400
                
                # Rename the column if it's the 'Lakhs' version
                if 'Approx. Value @CMP ₹ Lakhs' in df.columns:
                    df = df.rename(columns={'Approx. Value @CMP ₹ Lakhs': 'Approx. Value @CMP ₹ Lakh'})
                    df.to_excel(filepath, index=False)
                    print("Standardized column names")
            
            # Store the filepath and type in session
            session['uploaded_file'] = filepath
            session['message_type'] = 'generic' if is_generic else 'stock'
            print("File processed and stored in session")
            
            return jsonify({
                'message': 'File uploaded successfully',
                'groups_count': len(df['group_name'].unique())
            })
            
        except Exception as e:
            print(f"Error processing Excel file: {str(e)}")
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Error processing Excel file: {str(e)}'}), 400
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        # Clean up in case of error
        if 'filepath' in locals() and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': str(e)}), 500

@app.route('/send_messages', methods=['POST'])
@login_required
def send_messages():
    try:
        if 'uploaded_file' not in session:
            return jsonify({'error': 'Please upload a file first'}), 400
        
        filepath = session['uploaded_file']
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found. Please upload again'}), 400
        
        # Read the Excel file
        df = pd.read_excel(filepath)
        
        # Get message type and format preference
        data = request.get_json()
        message_type = data.get('type', session.get('message_type', 'stock'))
        
        if message_type == 'generic':
            # For generic messages, get the message text
            message_text = data.get('message')
            if not message_text:
                return jsonify({'error': 'No message provided'}), 400
        else:
            # For stock recommendations, get the format
            format_type = data.get('format', 'simple')
        
        # Initialize Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=chrome_options
            )
        except Exception as e:
            print(f"First attempt failed: {str(e)}")
            # Second attempt with different ChromeType
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install()),
                options=chrome_options
            )
        
        try:
            # Open WhatsApp Web
            driver.get('https://web.whatsapp.com')
            
            # Wait for WhatsApp to be ready (search box visible)
            print("Waiting for WhatsApp Web to be ready...")
            search_box = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true'][@data-tab='3']"))
            )
            print("WhatsApp Web is ready!")
            
            # Process messages based on type
            if message_type == 'generic':
                from whatsapp_utils import process_generic_messages
                results = process_generic_messages(driver, df, message_text, filepath)
            else:
                from whatsapp_utils import process_recommendations
                results = process_recommendations(driver, df, format_type, filepath)
            
            # Clean up
            driver.quit()
            
            # Clear the session
            if 'uploaded_file' in session:
                del session['uploaded_file']
            if 'message_type' in session:
                del session['message_type']
            
            return jsonify({
                'message': 'Messages processed',
                'details': {
                    'successful_groups': results['success'],
                    'failed_groups': results['failed']
                }
            })
            
        except Exception as e:
            print(f"Error waiting for WhatsApp: {str(e)}")
            return jsonify({'error': 'WhatsApp Web login timeout. Please try again.'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Ensure cleanup happens even if there's an error
        try:
            if 'driver' in locals():
                driver.quit()
            if 'uploaded_file' in session:
                filepath = session['uploaded_file']
                if os.path.exists(filepath):
                    os.remove(filepath)
                del session['uploaded_file']
            if 'message_type' in session:
                del session['message_type']
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_tables()
    app.run(debug=True, port=8080) 