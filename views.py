from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from app import app, db, login_manager
from models import User
from forms import LoginForm
from file_manager import generate_filelist, save_filelist
import os
from werkzeug.utils import secure_filename

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    filelist = generate_filelist(app.config['UPLOAD_FOLDER'])
    return render_template('dashboard.html', filelist=filelist)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('File successfully uploaded')
            return redirect(url_for('dashboard'))
    return render_template('upload.html')

@app.route('/generate')
@login_required
def generate():
    filelist = generate_filelist(app.config['UPLOAD_FOLDER'])
    save_filelist(filelist, 'patcher.txt')
    flash('Patchlist generated successfully')
    return redirect(url_for('dashboard'))
