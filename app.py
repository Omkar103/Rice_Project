from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import os
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import json

port = int(os.environ.get("PORT", 5000))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Disease Library Data
DISEASE_LIBRARY = {
    'Bacterial Blight': {
        'symptoms': 'Water-soaked lesions that turn yellow and then white',
        'causes': 'Xanthomonas oryzae bacteria',
        'treatment': 'Copper-based bactericides like Copper Oxychloride, resistant varieties (IR64, IR72)',
        'prevention': 'Field sanitation, avoid excessive nitrogen, crop rotation',
        'images': ['bacterial_blight_1.jpg', 'bacterial_blight_2.jpg']
    },
    'Blast (Leaf)': {
        'symptoms': 'Diamond-shaped lesions with gray centers and brown borders',
        'causes': 'Magnaporthe oryzae fungus',
        'treatment': 'Tricyclazole (Beam), Azoxystrobin (Amistar), Isoprothiolane (Fuji-One)',
        'prevention': 'Avoid dense planting, balanced fertilization (low nitrogen), resistant varieties',
        'images': ['blast_1.jpg', 'blast_2.jpg']
    },
    'Brown Spot': {
        'symptoms': 'Small oval brown spots on leaves, may have yellow halos',
        'causes': 'Cochliobolus miyabeanus fungus',
        'treatment': 'Mancozeb, Propiconazole, Azoxystrobin',
        'prevention': 'Maintain soil fertility (especially potassium), remove infected debris',
        'images': ['brown_spot_1.jpg', 'brown_spot_2.jpg']
    },
    'Healthy': {
        'description': 'No visible disease symptoms',
        'maintenance': 'Regular monitoring, balanced fertilization, proper irrigation',
        'images': ['healthy_1.jpg', 'healthy_2.jpg']
    }
}


# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 email TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 role TEXT DEFAULT 'user',
                 settings TEXT DEFAULT '{"dark_mode": false, "notifications": true, "language": "en"}')''')

    # Create predictions table
    c.execute('''CREATE TABLE IF NOT EXISTS predictions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 image_path TEXT NOT NULL,
                 disease TEXT NOT NULL,
                 confidence REAL NOT NULL,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')

    # Create default admin user if not exists
    try:
        c.execute("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                  ('admin', 'admin@riceai.com', generate_password_hash('admin123'), 'admin'))
    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()


init_db()

# Load the pre-trained model
# try:
#     model = tf.keras.models.load_model('models/rice_leaf_disease_model.h5')
#     print("Model loaded successfully")
#     print("Model input shape:", model.input_shape)  # Add this line
# except Exception as e:
#     print(f"Error loading model: {e}")
#     model = None

# Update the model loading code in app.py
try:
    model_path = os.path.join('models', 'rice_leaf_model.h5')
    print(f"Attempting to load model from: {model_path}")
    model = tf.keras.models.load_model(model_path)
    print("Model loaded successfully")
    print(f"Model input shape: {model.input_shape}")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

# @app.route('/')
# def home():
#     if 'user_id' in session:
#         return redirect(url_for('dashboard'))
#     return render_template('index.html')
@app.route('/')
def home():
    session.clear()  # Clears all session data
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, password, role FROM users WHERE username = ?", (username,))
        user = c.fetchone()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['role'] = user[2]
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = generate_password_hash(data.get('password'))

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                  (username, email, password))
        conn.commit()
        user_id = c.lastrowid

        session['user_id'] = user_id
        session['role'] = 'user'
        return jsonify({'success': True, 'redirect': url_for('dashboard')})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Username or email already exists'})
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        # Get user's prediction history
        c.execute(
            "SELECT disease, confidence, timestamp FROM predictions WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5",
            (session['user_id'],))
        history = c.fetchall()

        # Get statistics
        c.execute("SELECT COUNT(*) FROM predictions WHERE user_id = ?", (session['user_id'],))
        total_predictions = c.fetchone()[0]

        c.execute("SELECT disease, COUNT(*) FROM predictions WHERE user_id = ? GROUP BY disease",
                  (session['user_id'],))
        disease_stats = c.fetchall()

        # Get user settings
        c.execute("SELECT settings FROM users WHERE id = ?", (session['user_id'],))
        settings_row = c.fetchone()
        settings = json.loads(settings_row[0]) if settings_row else {'dark_mode': False, 'notifications': True,
                                                                     'language': 'en'}

        return render_template('dashboard.html',
                               history=history,
                               total_predictions=total_predictions,
                               disease_stats=disease_stats,
                               settings=settings,
                               DISEASE_LIBRARY=DISEASE_LIBRARY)
    except Exception as e:
        print(f"Error in dashboard: {e}")
        return render_template('dashboard.html',
                               history=[],
                               total_predictions=0,
                               disease_stats=[],
                               settings={'dark_mode': False, 'notifications': True, 'language': 'en'},
                               DISEASE_LIBRARY=DISEASE_LIBRARY)
    finally:
        if 'conn' in locals():
            conn.close()


# @app.route('/classify', methods=['POST'])
# def classify():
#     if 'user_id' not in session:
#         return jsonify({'error': 'Unauthorized'}), 401
#     if not model:
#         return jsonify({'error': 'Model not loaded'}), 500
#
#     if 'image' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
#
#     file = request.files['image']
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400
#
#     try:
#         # Validate file extension
#         allowed_extensions = {'jpg', 'jpeg', 'png'}
#         if '.' not in file.filename or file.filename.split('.')[-1].lower() not in allowed_extensions:
#             return jsonify({'error': 'Invalid file type. Please upload JPG, JPEG, or PNG.'}), 400
#
#         # Save the uploaded image
#         uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
#         os.makedirs(uploads_dir, exist_ok=True)
#         image_path = os.path.join('uploads', f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
#         full_path = os.path.join(app.root_path, 'static', image_path)
#         file.save(full_path)
#
#         # Process and predict
#         # image = Image.open(full_path).convert('RGB')
#         # image = image.resize((224, 224))  # Adjust to your model's input size
#         # image_array = np.array(image) / 255.0
#         #
#         # if len(image_array.shape) != 3 or image_array.shape[-1] != 3:
#         #     return jsonify({'error': 'Invalid image dimensions'}), 400
#         #
#         # image_array = np.expand_dims(image_array, axis=0)
#
#         image = Image.open(full_path).convert('RGB')
#         image = image.resize((150, 150))  # Resize to 150x150 if your model was trained on this
#         image_array = np.array(image) / 255.0
#
#         # Flatten the image if the model expects a flat input
#         image_array = image_array.reshape(1, -1)  # Converts to shape (1, 150 * 150 * 3 = 67500)
#
#         # Optional: check against model.input_shape
#         expected_shape = model.input_shape[1]
#         if image_array.shape[1] != expected_shape:
#             return jsonify(
#                 {'error': f'Invalid image shape: expected {expected_shape}, got {image_array.shape[1]}'}), 400
#
#         prediction = model.predict(image_array)
#         class_idx = np.argmax(prediction, axis=1)[0]
#         confidence = float(np.max(prediction))
#         disease = get_disease_name(class_idx)
#         recommendation = get_recommendation(disease)
#
#         # Save prediction to database
#         try:
#             conn = sqlite3.connect('database.db')
#             c = conn.cursor()
#             c.execute("INSERT INTO predictions (user_id, image_path, disease, confidence) VALUES (?, ?, ?, ?)",
#                       (session['user_id'], image_path, disease, confidence))
#             conn.commit()
#         except sqlite3.Error as e:
#             print(f"Database error: {e}")
#         finally:
#             if 'conn' in locals():
#                 conn.close()
#
#         return jsonify({
#             'success': True,
#             'disease': disease,
#             'confidence': confidence,
#             'recommendation': recommendation,
#             'image_path': '/' + image_path
#         })
#
#     except Exception as e:
#         print(f"Error in classification: {e}")
#         return jsonify({'error': str(e)}), 500

@app.route('/classify', methods=['POST'])
def classify():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    if not model:
        return jsonify({'error': 'Model not loaded'}), 500

    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Validate file extension
        allowed_extensions = {'jpg', 'jpeg', 'png'}
        if '.' not in file.filename or file.filename.split('.')[-1].lower() not in allowed_extensions:
            return jsonify({'error': 'Invalid file type. Please upload JPG, JPEG, or PNG.'}), 400

        # Save the uploaded image
        uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        image_path = os.path.join('uploads', f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        full_path = os.path.join(app.root_path, 'static', image_path)
        file.save(full_path)

        # Process and predict
        image = Image.open(full_path).convert('RGB')

        # Resize to match model's expected input shape
        target_size = (150,150)  # Based on the error message
        image = image.resize(target_size)

        # Convert to numpy array and normalize
        image_array = np.array(image) / 255.0

        # Check if we need to flatten based on model input shape
        if model.input_shape == (None, 150528):  # 150*150*3=67500? Wait no, 150*150*3=67500, but error shows 150528
            # Flatten the image
            image_array = image_array.reshape(1, -1)  # This will create (1, 150*150*3)

            # Check if we need to pad or adjust dimensions
            if image_array.shape[1] < 150528:
                # Pad with zeros if needed
                padding = np.zeros((1, 150528 - image_array.shape[1]))
                image_array = np.hstack((image_array, padding))
            elif image_array.shape[1] > 150528:
                # Truncate if needed
                image_array = image_array[:, :150528]
        else:
            # Add batch dimension if model expects 4D input
            image_array = np.expand_dims(image_array, axis=0)

        # Debug print to check the shape
        print(f"Input shape to model: {image_array.shape}")
        print(f"Model expects: {model.input_shape}")

        # Make prediction
        prediction = model.predict(image_array)
        class_idx = np.argmax(prediction, axis=1)[0]
        confidence = float(np.max(prediction))
        disease = get_disease_name(class_idx)
        recommendation = get_recommendation(disease)

        # Save prediction to database
        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("INSERT INTO predictions (user_id, image_path, disease, confidence) VALUES (?, ?, ?, ?)",
                      (session['user_id'], image_path, disease, confidence))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

        return jsonify({
            'success': True,
            'disease': disease,
            'confidence': confidence,
            'recommendation': recommendation,
            'image_path': '/' + image_path,
            'reset': True
        })

    except Exception as e:
        print(f"Error in classification: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/disease-info/<disease_name>')
def disease_info(disease_name):
    disease_data = DISEASE_LIBRARY.get(disease_name, {})
    if not disease_data:
        return jsonify({'error': 'Disease not found'}), 404

    # Add full image paths
    if 'images' in disease_data:
        disease_data['images'] = [f"/static/images/diseases/{img}" for img in disease_data['images']]
    return jsonify(disease_data)


@app.route('/diseases')
def list_diseases():
    return jsonify({'diseases': list(DISEASE_LIBRARY.keys())})


@app.route('/chatbot', methods=['POST'])
def chatbot():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    question = data.get('question', '').lower().strip()

    # Check for specific disease queries
    for disease_name in DISEASE_LIBRARY:
        if disease_name.lower() in question:
            disease_info = DISEASE_LIBRARY[disease_name].copy()
            disease_info['images'] = [f"/static/images/diseases/{img}" for img in disease_info.get('images', [])]
            return jsonify({
                'type': 'disease_info',
                'disease': disease_name,
                'answer': f"Information about {disease_name}:",
                **disease_info
            })

    # Handle general questions
    responses = {
        'hello': {'type': 'greeting', 'answer': 'Hello! I can help with rice disease identification and management.'},
        'hi': {'type': 'greeting', 'answer': 'Hi there! Ask me about rice plant diseases.'},
        'treatment': {
            'type': 'general_info',
            'answer': 'Common treatments include:',
            'details': [
                'Fungicides (Tricyclazole for blast)',
                'Bactericides (Copper compounds for blight)',
                'Resistant varieties',
                'Field sanitation'
            ]
        },
        'prevent': {
            'type': 'general_info',
            'answer': 'Prevention methods:',
            'details': [
                'Crop rotation',
                'Balanced fertilization',
                'Disease-free seeds',
                'Proper water management'
            ]
        },
        'symptom': {
            'type': 'guidance',
            'answer': 'Common symptoms:',
            'examples': [
                'Bacterial blight: Water-soaked lesions',
                'Blast: Diamond-shaped gray spots',
                'Brown spot: Small oval brown spots'
            ]
        },
        'list': {
            'type': 'disease_list',
            'answer': 'I know about:',
            'diseases': list(DISEASE_LIBRARY.keys())
        },
        'default': {
            'type': 'guidance',
            'answer': "Ask me about:",
            'suggestions': [
                "Symptoms of specific diseases",
                "Treatment options",
                "Prevention methods",
                "List of known diseases"
            ]
        }
    }

    # Find matching response
    answer = responses['default']
    for key in responses:
        if key in question:
            answer = responses[key]
            break

    return jsonify(answer)


@app.route('/update-settings', methods=['POST'])
def update_settings():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        settings = request.get_json()
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("UPDATE users SET settings = ? WHERE id = ?",
                  (json.dumps(settings), session['user_id']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating settings: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


def get_disease_name(class_idx):
    disease_dict = {
        0: 'Bacterial Blight',
        1: 'Blast (Leaf)',
        2: 'Healthy',
        3: 'Brown Spot',
    }
    return disease_dict.get(class_idx, 'Unknown Disease')


def get_recommendation(disease):
    recommendations = {
        'Bacterial Blight': '🔹 Use copper-based bactericides\n🔹 Improve field drainage\n🔹 Avoid excess nitrogen\n🔹 Practice crop rotation',
        'Blast (Leaf)': '🔹 Apply fungicides (Tricyclazole)\n🔹 Balanced fertilization\n🔹 Proper spacing\n🔹 Resistant varieties',
        'Brown Spot': '🔹 Apply fungicides\n🔹 Maintain soil potassium\n🔹 Remove infected debris',
        'Healthy': '✅ Plant is healthy!\n🔹 Continue monitoring\n🔹 Maintain good practices'
    }
    return recommendations.get(disease, 'Consult an agricultural expert.')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port)
