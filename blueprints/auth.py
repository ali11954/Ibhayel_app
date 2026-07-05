from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, User, Employee, Attendance, FinancialTransaction, Salary
from utils import role_required
from config import Config

auth = Blueprint('auth', __name__)


@auth.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('landing.html')
    try:
        today = datetime.now().date()
        total_employees = Employee.query.filter_by(is_active=True).count()
        today_attendance = Attendance.query.filter_by(date=today, attendance_status='present').count()
        pending_transactions = FinancialTransaction.query.filter_by(is_settled=False).count()
        pending_salaries = Salary.query.filter_by(is_paid=False).count()
        stats = {
            'total_employees': total_employees,
            'today_attendance': today_attendance,
            'pending_transactions': pending_transactions,
            'pending_salaries': pending_salaries
        }
        recent_attendance = Attendance.query.filter(Attendance.attendance_status == 'present').order_by(
            Attendance.date.desc()).limit(5).all()

        salaries_data = []
        for i in range(6):
            date = datetime.now() - timedelta(days=30 * i)
            month_year = date.strftime('%m-%Y')
            total = db.session.query(func.sum(Salary.total_salary)).filter_by(month_year=month_year).scalar() or 0
            salaries_data.append({'month': date.strftime('%b'), 'total': float(total)})

        regions_result = db.session.query(
            Employee.region,
            db.func.count(Employee.id).label('count')
        ).filter(
            Employee.is_active == True,
            Employee.region != None,
            Employee.region != ''
        ).group_by(Employee.region).all()

        regions_data = []
        for row in regions_result:
            if row[0]:
                regions_data.append({
                    'region': row[0],
                    'count': row[1]
                })

        return render_template('index.html',
                               stats=stats,
                               recent_attendance=recent_attendance,
                               salaries_data=salaries_data,
                               regions_data=regions_data,
                               now=datetime.now())
    except Exception as e:
        print(f"Error in index: {e}")
        import traceback
        traceback.print_exc()
        return render_template('index.html',
                               stats={'total_employees': 0, 'today_attendance': 0, 'pending_transactions': 0,
                                      'pending_salaries': 0},
                               recent_attendance=[],
                               salaries_data=[],
                               regions_data=[],
                               now=datetime.now())


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
