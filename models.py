from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# ==================== User Model ====================
class User(UserMixin, db.Model):
    """نموذج المستخدمين والصلاحيات"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def has_role(self, role):
        return self.role == role or self.role == 'admin'

    def has_any_role(self, *roles):
        return self.role in roles or self.role == 'admin'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active
        }


# ==================== Employee Model ====================
class Employee(db.Model):
    """نموذج الموظفين (العمال)"""
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    card_number = db.Column(db.String(20), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    job_title = db.Column(db.String(100))
    region = db.Column(db.String(100))
    is_resident = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(20))
    salary = db.Column(db.Float, default=60000)
    daily_allowance = db.Column(db.Float, default=500)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    company = db.relationship('Company', backref='employees')

    def get_attendance_count(self, start_date, end_date):
        from models import Attendance
        return Attendance.query.filter(
            Attendance.employee_id == self.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date,
            Attendance.attendance_status == 'present'  # استخدم attendance_status بدلاً من is_present
        ).count()

    def get_transactions_sum(self, transaction_type, start_date=None, end_date=None):
        from models import FinancialTransaction
        query = FinancialTransaction.query.filter(
            FinancialTransaction.employee_id == self.id,
            FinancialTransaction.transaction_type == transaction_type,
            FinancialTransaction.is_settled == False
        )
        if start_date and end_date:
            query = query.filter(
                FinancialTransaction.date >= start_date,
                FinancialTransaction.date <= end_date
            )
        return sum(t.amount for t in query.all()) or 0

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'card_number': self.card_number,
            'code': self.code,
            'job_title': self.job_title,
            'region': self.region,
            'is_resident': self.is_resident,
            'phone': self.phone,
            'salary': self.salary,
            'is_active': self.is_active
        }


# ==================== Attendance Model ====================
class Attendance(db.Model):
    """نموذج الحضور اليومي"""
    __tablename__ = 'attendances'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    attendance_type = db.Column(db.String(20), default='individual')  # individual, group
    attendance_status = db.Column(db.String(20), default='present')  # present, late, sick, absent
    late_minutes = db.Column(db.Integer, default=0)
    sick_leave = db.Column(db.Boolean, default=False)
    sick_leave_days = db.Column(db.Integer, default=0)
    check_in_time = db.Column(db.Time)
    check_out_time = db.Column(db.Time)
    notes = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref='attendances')
    creator = db.relationship('User', backref='created_attendances')

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date', name='unique_employee_date'),
    )

    @classmethod
    def get_daily_attendance(cls, date):
        return cls.query.filter_by(date=date, attendance_status='present').all()

    @classmethod
    def get_monthly_attendance(cls, employee_id, start_date, end_date):
        return cls.query.filter(
            cls.employee_id == employee_id,
            cls.date >= start_date,
            cls.date <= end_date,
            cls.attendance_status == 'present'
        ).count()


# ==================== Financial Models ====================
class FinancialTransaction(db.Model):
    """نموذج المعاملات المالية"""
    __tablename__ = 'financial_transactions'

    TRANSACTION_TYPES = {
        'advance': 'سلفة',
        'overtime': 'إضافي',
        'deduction': 'خصم',
        'penalty': 'جزاء'
    }

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)
    is_settled = db.Column(db.Boolean, default=False)
    settled_date = db.Column(db.Date)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref='transactions')
    creator = db.relationship('User', backref='created_transactions')

    def get_type_name(self):
        return self.TRANSACTION_TYPES.get(self.transaction_type, self.transaction_type)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'transaction_type': self.transaction_type,
            'type_name': self.get_type_name(),
            'amount': self.amount,
            'description': self.description,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'is_settled': self.is_settled
        }


class Salary(db.Model):
    """نموذج الرواتب الشهرية"""
    __tablename__ = 'salaries'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    month_year = db.Column(db.String(10), nullable=False)
    base_salary = db.Column(db.Float, default=0)
    attendance_days = db.Column(db.Integer, default=0)
    attendance_amount = db.Column(db.Float, default=0)
    daily_allowance_amount = db.Column(db.Float, default=0)
    overtime_amount = db.Column(db.Float, default=0)
    advance_amount = db.Column(db.Float, default=0)
    deduction_amount = db.Column(db.Float, default=0)
    penalty_amount = db.Column(db.Float, default=0)
    total_salary = db.Column(db.Float, default=0)
    is_paid = db.Column(db.Boolean, default=False)
    paid_date = db.Column(db.Date)
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref='salaries')

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'month_year', name='unique_employee_month'),
    )

    def calculate(self, attendance_days, daily_allowance, overtime, advance, deduction, penalty):
        self.attendance_days = attendance_days
        self.attendance_amount = (self.base_salary / 30) * attendance_days
        self.daily_allowance_amount = daily_allowance * attendance_days if daily_allowance else 0
        self.overtime_amount = overtime
        self.advance_amount = advance
        self.deduction_amount = deduction
        self.penalty_amount = penalty
        self.total_salary = (
                self.attendance_amount +
                self.daily_allowance_amount +
                self.overtime_amount -
                self.advance_amount -
                self.deduction_amount -
                self.penalty_amount
        )
        return self.total_salary

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'month_year': self.month_year,
            'base_salary': self.base_salary,
            'attendance_days': self.attendance_days,
            'attendance_amount': self.attendance_amount,
            'daily_allowance_amount': self.daily_allowance_amount,
            'overtime_amount': self.overtime_amount,
            'advance_amount': self.advance_amount,
            'deduction_amount': self.deduction_amount,
            'penalty_amount': self.penalty_amount,
            'total_salary': self.total_salary,
            'is_paid': self.is_paid
        }


# ==================== Evaluation Model ====================
class Evaluation(db.Model):
    """نموذج تقييم العمال"""
    __tablename__ = 'evaluations'

    EVALUATION_TYPES = {
        'supervisor': 'تقييم مشرف',
        'contractor': 'تقييم متعهد'
    }

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    evaluation_type = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref='evaluations')
    evaluator = db.relationship('User', backref='evaluations')

    def get_type_name(self):
        return self.EVALUATION_TYPES.get(self.evaluation_type, self.evaluation_type)

    def get_rating(self):
        if self.score >= 9:
            return 'ممتاز'
        elif self.score >= 7:
            return 'جيد جداً'
        elif self.score >= 5:
            return 'جيد'
        elif self.score >= 3:
            return 'مقبول'
        else:
            return 'ضعيف'

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'evaluation_type': self.evaluation_type,
            'type_name': self.get_type_name(),
            'score': self.score,
            'rating': self.get_rating(),
            'comments': self.comments,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None
        }


# ==================== Company Models ====================
class Company(db.Model):
    """نموذج الشركات"""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(100))
    location = db.Column(db.String(100))
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'region': self.region,
            'location': self.location,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'email': self.email
        }


class Contract(db.Model):
    """نموذج العقود"""
    __tablename__ = 'contracts'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    contract_type = db.Column(db.String(20))  # annual, monthly
    contract_value = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    amount_received = db.Column(db.Float, default=0)
    remaining_amount = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='active')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company', backref='contracts')

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else '',
            'contract_type': self.contract_type,
            'contract_value': self.contract_value,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'amount_received': self.amount_received,
            'remaining_amount': self.remaining_amount,
            'status': self.status
        }


class Invoice(db.Model):
    """نموذج الفواتير"""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'))
    invoice_number = db.Column(db.String(50), unique=True)
    amount = db.Column(db.Float, nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    is_paid = db.Column(db.Boolean, default=False)
    paid_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    contract = db.relationship('Contract', backref='invoices')

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'invoice_number': self.invoice_number,
            'amount': self.amount,
            'invoice_date': self.invoice_date.strftime('%Y-%m-%d') if self.invoice_date else None,
            'due_date': self.due_date.strftime('%Y-%m-%d') if self.due_date else None,
            'is_paid': self.is_paid,
            'paid_date': self.paid_date.strftime('%Y-%m-%d') if self.paid_date else None
        }