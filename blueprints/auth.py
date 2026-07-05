from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, User, Employee, Attendance, FinancialTransaction, Salary
from utils import role_required
from config import Config

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')


        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('auth.index'))
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    return render_template('auth/login.html')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('auth.login'))


@auth.route('/users')
@login_required
@role_required('admin')
def users_list():
    users = User.query.all()
    return render_template('users/users.html', users=users)


@auth.route('/users/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        if User.query.filter_by(username=username).first():
            flash('اسم المستخدم موجود مسبقاً', 'danger')
            return redirect(url_for('auth.add_user'))

        user = User(
            username=username,
            password=generate_password_hash(request.form.get('password')),
            full_name=request.form.get('full_name'),
            role=request.form.get('role')
        )
        db.session.add(user)
        db.session.commit()
        flash('تم إضافة المستخدم بنجاح', 'success')
        return redirect(url_for('auth.users_list'))
    return render_template('users/add_user.html', roles=Config.ROLES)


@auth.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.role = request.form.get('role')
        if request.form.get('password'):
            user.password = generate_password_hash(request.form.get('password'))
        db.session.commit()
        flash('تم تحديث المستخدم بنجاح', 'success')
        return redirect(url_for('auth.users_list'))

    roles = {
        'admin': 'مدير النظام',
        'supervisor': 'مشرف',
        'finance': 'موظف مالي',
        'viewer': 'مشاهد'
    }
    return render_template('users/edit_user.html', user=user, roles=roles)


@auth.route('/users/delete/<int:user_id>')
@login_required
@role_required('admin')
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('لا يمكن حذف المستخدم الحالي', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('تم حذف المستخدم بنجاح', 'success')
    return redirect(url_for('auth.users_list'))


@auth.route('/check-username')
def check_username():
    username = request.args.get('username')

    exists = User.query.filter_by(username=username).first() is not None

    return jsonify({
        "exists": exists
    })
