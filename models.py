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


# ==================== Attendance Model ====================
class Attendance(db.Model):
    """نموذج الحضور اليومي"""
    __tablename__ = 'attendances'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    attendance_type = db.Column(db.String(20), default='individual')  # individual, group
    attendance_status = db.Column(db.String(20), default='present')  # present, late, sick, absent, annual_leave
    late_minutes = db.Column(db.Integer, default=0)
    sick_leave = db.Column(db.Boolean, default=False)
    sick_leave_days = db.Column(db.Integer, default=0)
    annual_leave_days = db.Column(db.Integer, default=0)  # أيام الإجازة السنوية بدون أجر
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

    def get_status_display(self):
        """عرض الحالة بشكل مفهوم"""
        status_map = {
            'present': 'حاضر',
            'absent': 'غائب',
            'late': 'متأخر',
            'sick': 'إجازة مرضية',
            'annual_leave': 'إجازة سنوية'
        }
        return status_map.get(self.attendance_status, self.attendance_status)

    def is_paid_day(self):
        """هل اليوم مدفوع الأجر؟ - الإجازة السنوية بدون أجر"""
        paid_statuses = ['present', 'late']  # فقط الحاضر والمتأخر يحسب لهم أجر
        return self.attendance_status in paid_statuses

    def get_leave_days(self):
        """الحصول على عدد أيام الإجازة حسب النوع"""
        if self.attendance_status == 'sick':
            return self.sick_leave_days
        elif self.attendance_status == 'annual_leave':
            return self.annual_leave_days
        return 0

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

    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=True)
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id], backref='financial_transaction')

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


    def has_financial_impact(self):
        """التحقق من وجود تأثير مالي"""
        return self.is_settled or self.journal_entry_id is not None

    def can_delete(self):
        """التحقق من إمكانية حذف المعاملة"""
        # لا يمكن حذف المعاملة إذا:
        # 1. تم ترحيلها (is_settled = True)
        # 2. لها قيد محاسبي مرتبط
        return not self.is_settled and self.journal_entry_id is None


# ==================== Employee Model (النسخة النهائية) ====================
class Employee(db.Model):
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
    employee_type = db.Column(db.String(20), default='worker')
    supervisor_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    supervised_workers = db.relationship('Employee', backref=db.backref('supervisor', remote_side=[id]), lazy=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref='employee_profile')
    worker_type = db.Column(db.String(20), default='permanent')
    basic_salary = db.Column(db.Float, default=2000)
    clothing_allowance = db.Column(db.Float, default=24480)
    health_card_allowance = db.Column(db.Float, default=15000)
    monthly_insurance = db.Column(db.Float, default=10800)
    contractor_tax = db.Column(db.Float, default=500000)
    contractor_zakat = db.Column(db.Float, default=75000)
    allowances_updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ========== الدالة الوحيدة لحساب الراتب ==========
    def calculate_salary_breakdown(self, attendance_days, paid_leave_days=0):
        """
        حساب توزيع الراتب مع دعم الإجازات المدفوعة
        """
        MONTHLY_DAYS = 30
        BASE_WORKER = 60000
        DAILY_RATE = BASE_WORKER / MONTHLY_DAYS
        DAILY_RESIDENT = 500

        MONTHLY_CLOTHING = 2033.33
        MONTHLY_HEALTH = 1250.00
        MONTHLY_INSURANCE = 10800.00

        # إجمالي أيام الدفع (حضور + إجازة مدفوعة)
        total_paid_days = attendance_days + paid_leave_days

        ratio = total_paid_days / MONTHLY_DAYS if total_paid_days > 0 else 0

        basic_payout = DAILY_RATE * total_paid_days
        resident_payout = DAILY_RESIDENT * total_paid_days
        cash_payout = basic_payout + resident_payout

        clothing_payout = MONTHLY_CLOTHING * ratio
        health_payout = MONTHLY_HEALTH * ratio
        insurance_payout = MONTHLY_INSURANCE * ratio

        difference = self.salary - BASE_WORKER
        contractor_profit = (difference * ratio) - (clothing_payout + health_payout + insurance_payout)

        return {
            'attendance_days': attendance_days,
            'paid_leave_days': paid_leave_days,
            'total_paid_days': total_paid_days,
            'ratio': ratio,
            'company_payment': self.salary * ratio,
            'cash_payout': cash_payout,
            'basic_salary': basic_payout,
            'resident_allowance': resident_payout,
            'clothing_allowance': clothing_payout,
            'health_card': health_payout,
            'insurance': insurance_payout,
            'contractor_profit': contractor_profit
        }

    # ========== دوال مساعدة ==========
    def get_attendance_count(self, start_date, end_date):
        from models import Attendance
        return Attendance.query.filter(
            Attendance.employee_id == self.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date,
            Attendance.attendance_status == 'present'
        ).count()

    def get_transactions_sum(self, transaction_type, start_date=None, end_date=None, include_settled=False):
        from models import FinancialTransaction
        query = FinancialTransaction.query.filter(
            FinancialTransaction.employee_id == self.id,
            FinancialTransaction.transaction_type == transaction_type
        )
        if not include_settled:
            query = query.filter(FinancialTransaction.is_settled == False)
        if start_date and end_date:
            query = query.filter(
                FinancialTransaction.date >= start_date,
                FinancialTransaction.date <= end_date
            )
        return sum(t.amount for t in query.all()) or 0

    @property
    def is_worker(self):
        return self.employee_type == 'worker'

    @property
    def company_name(self):
        return self.company.name if self.company else None

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'card_number': self.card_number,
            'code': self.code, 'job_title': self.job_title, 'region': self.region,
            'is_resident': self.is_resident, 'phone': self.phone, 'salary': self.salary,
            'is_active': self.is_active, 'employee_type': self.employee_type,
            'company_id': self.company_id, 'company_name': self.company_name,
            'supervisor_id': self.supervisor_id
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

    # تخزين درجات المعايير كـ JSON
    criteria_scores = db.Column(db.Text)

    # ✅ حقول المنطقة والموقع (جديدة)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)

    # العلاقات
    employee = db.relationship('Employee', backref='evaluations')
    evaluator = db.relationship('User', backref='evaluations')
    region = db.relationship('Region', foreign_keys=[region_id], backref='evaluations')
    location = db.relationship('Location', foreign_keys=[location_id], backref='evaluations')

    def set_criteria_scores(self, scores_list):
        """تخزين درجات المعايير"""
        import json
        self.criteria_scores = json.dumps(scores_list)

    def get_criteria_scores(self):
        """استرجاع درجات المعايير"""
        import json
        return json.loads(self.criteria_scores) if self.criteria_scores else []

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
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'criteria_scores': self.get_criteria_scores(),
            'region_id': self.region_id,
            'region_name': self.region.name if self.region else None,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None
        }
# ==================== Company Region Location Models ====================
class Company(db.Model):
    """نموذج الشركات"""
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات - استخدام أسماء مختلفة لتجنب التضارب
    company_regions = db.relationship('Region', backref='company', lazy=True, cascade='all, delete-orphan')
    company_employees = db.relationship('Employee', backref='employee_company', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_person': self.contact_person,
            'phone': self.phone,
            'email': self.email,
            'regions_count': len(self.company_regions),
            'employees_count': len(self.company_employees)
        }


class Region(db.Model):
    """نموذج المناطق (تابعة لشركة)"""
    __tablename__ = 'regions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات
    region_locations = db.relationship('Location', backref='region', lazy=True, cascade='all, delete-orphan')

    # فريد لكل شركة (لا يمكن تكرار نفس المنطقة لنفس الشركة)
    __table_args__ = (db.UniqueConstraint('company_id', 'name', name='unique_company_region'),)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'locations_count': len(self.region_locations)
        }


class Location(db.Model):
    """نموذج المواقع (تابعة لمنطقة)"""
    __tablename__ = 'locations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    address = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # فريد لكل منطقة (لا يمكن تكرار نفس الموقع لنفس المنطقة)
    __table_args__ = (db.UniqueConstraint('region_id', 'name', name='unique_region_location'),)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'region_id': self.region_id,
            'region_name': self.region.name if self.region else None,
            'company_id': self.region.company_id if self.region else None,
            'company_name': self.region.company.name if self.region and self.region.company else None,
            'address': self.address,
            'notes': self.notes
        }


# ==================== Salary Model ====================
class Salary(db.Model):
    __tablename__ = 'salaries'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    month_year = db.Column(db.String(20), nullable=False)
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

    # حقول التوزيع التفصيلية
    basic_salary_amount = db.Column(db.Float, default=0)
    resident_allowance_amount = db.Column(db.Float, default=0)
    clothing_allowance_amount = db.Column(db.Float, default=0)
    health_card_amount = db.Column(db.Float, default=0)
    insurance_amount = db.Column(db.Float, default=0)
    contractor_profit = db.Column(db.Float, default=0)

    employee = db.relationship('Employee', backref='salaries')

    __table_args__ = (db.UniqueConstraint('employee_id', 'month_year', name='unique_employee_month'),)

    def get_breakdown(self):
        return {
            'employee_payout': {
                'basic_salary': self.basic_salary_amount,
                'resident_allowance': self.resident_allowance_amount,
                'total': self.basic_salary_amount + self.resident_allowance_amount
            },
            'contractor_costs': {
                'clothing': self.clothing_allowance_amount,
                'health_card': self.health_card_amount,
                'insurance': self.insurance_amount,
                'total': self.clothing_allowance_amount + self.health_card_amount + self.insurance_amount
            },
            'final_salary': self.total_salary,
            'contractor_profit': self.contractor_profit
        }

    def to_dict(self):
        return {
            'id': self.id, 'employee_name': self.employee.name if self.employee else None,
            'month_year': self.month_year, 'attendance_days': self.attendance_days,
            'basic_salary': self.basic_salary_amount, 'resident_allowance': self.resident_allowance_amount,
            'cash_payout': self.basic_salary_amount + self.resident_allowance_amount,
            'clothing': self.clothing_allowance_amount, 'health_card': self.health_card_amount,
            'insurance': self.insurance_amount, 'contractor_profit': self.contractor_profit,
            'total_salary': self.total_salary, 'is_paid': self.is_paid
        }

    def calculate_from_preparation_detail(self, preparation_detail):
        """حساب الراتب من تفاصيل تحضير الدوام"""
        from models import Employee

        employee = Employee.query.get(self.employee_id)
        if employee and employee.employee_type == 'worker':
            breakdown = employee.calculate_salary_breakdown(preparation_detail.attendance_days)

            self.basic_salary_amount = breakdown['basic_salary']
            self.resident_allowance_amount = breakdown['resident_allowance']
            self.clothing_allowance_amount = breakdown['clothing_allowance']
            self.health_card_amount = breakdown['health_card']
            self.insurance_amount = breakdown['insurance']
            self.contractor_profit = breakdown['contractor_profit']
            self.attendance_days = preparation_detail.attendance_days
            self.attendance_amount = breakdown['cash_payout']
            self.total_salary = breakdown['cash_payout']
        else:
            # للمشرفين والإداريين
            self.attendance_days = preparation_detail.attendance_days
            daily_rate = self.base_salary / 30
            self.attendance_amount = daily_rate * preparation_detail.attendance_days
            self.daily_allowance_amount = preparation_detail.daily_allowance
            self.total_salary = self.attendance_amount + self.daily_allowance_amount

        return self.total_salary

# ==================== نموذج تكاليف العمال الشهرية ====================

class LaborMonthlyCost(db.Model):
    """نموذج التكاليف الشهرية للعمال (بالإضافة للرواتب)"""
    __tablename__ = 'labor_monthly_costs'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    month_year = db.Column(db.String(20), nullable=False)  # MM-YYYY

    # التكاليف الأساسية
    basic_salary_cost = db.Column(db.Float, default=0)  # الراتب الأساسي
    resident_allowance_cost = db.Column(db.Float, default=0)  # بدل السكن

    # التكاليف الإضافية
    insurance_cost = db.Column(db.Float, default=0)  # التأمين الشهري
    clothing_allowance_cost = db.Column(db.Float, default=0)  # بدل الملابس (تقسيط سنوي)
    health_card_cost = db.Column(db.Float, default=0)  # البطائق الصحية (تقسيط سنوي)

    # إجمالي تكلفة العامل
    total_cost = db.Column(db.Float, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    employee = db.relationship('Employee', backref='monthly_costs')

    __table_args__ = (db.UniqueConstraint('employee_id', 'month_year', name='unique_employee_month_cost'),)

    def calculate_total_cost(self):
        """حساب إجمالي التكلفة الشهرية"""
        self.total_cost = (
            self.basic_salary_cost +
            self.resident_allowance_cost +
            self.insurance_cost +
            self.clothing_allowance_cost +
            self.health_card_cost
        )
        return self.total_cost

    # إضافة دوال مساعدة لنموذج Employee
    def get_transactions_summary(self, start_date=None, end_date=None):
        from models import FinancialTransaction
        query = FinancialTransaction.query.filter(
            FinancialTransaction.employee_id == self.id,
            FinancialTransaction.is_settled == False
        )
        if start_date and end_date:
            query = query.filter(
                FinancialTransaction.date >= start_date,
                FinancialTransaction.date <= end_date
            )
        transactions = query.all()
        summary = {'advance': 0, 'overtime': 0, 'deduction': 0, 'penalty': 0}
        for t in transactions:
            if t.transaction_type in summary:
                summary[t.transaction_type] += t.amount
        return summary

    # ربط الدالة
    Employee.get_transactions_summary = get_transactions_summary

class ContractorAnnualCost(db.Model):
    """نموذج التكاليف السنوية للمتعهدين"""
    __tablename__ = 'contractor_annual_costs'

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    # التكاليف السنوية للمتعهد
    tax_amount = db.Column(db.Float, default=500000)  # ضريبة سنوية
    zakat_amount = db.Column(db.Float, default=75000)  # زكاة سنوية

    # الحالة
    is_paid = db.Column(db.Boolean, default=False)
    paid_date = db.Column(db.Date)
    payment_reference = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    company = db.relationship('Company', backref='contractor_costs')

    __table_args__ = (db.UniqueConstraint('year', 'company_id', name='unique_year_company'),)


# ==================== حسابات المحاسبة الجديدة ====================

def create_labor_accounts():
    """إنشاء الحسابات المحاسبية لرواتب العمال"""
    from models import Account, db

    labor_accounts = [
        # مصروفات الرواتب
        ('511001', 'Labor Basic Salary', 'رواتب العمال الأساسية', 'expense', 'debit'),
        ('511002', 'Labor Resident Allowance', 'بدل سكن العمال', 'expense', 'debit'),
        ('511003', 'Labor Insurance', 'تأمين العمال', 'expense', 'debit'),
        ('511004', 'Labor Clothing Allowance', 'بدل ملابس العمال', 'expense', 'debit'),
        ('511005', 'Labor Health Cards', 'بطائق صحية للعمال', 'expense', 'debit'),

        # مخصصات وخصوم
        ('211001', 'Labor Salaries Payable', 'رواتب العمال المستحقة', 'liability', 'credit'),
        ('211002', 'Labor Allowances Payable', 'بدلات العمال المستحقة', 'liability', 'credit'),
        ('211003', 'Insurance Payable', 'تأمينات مستحقة', 'liability', 'credit'),

        # مصروفات المتعهدين
        ('521001', 'Contractor Tax', 'ضريبة المتعهدين', 'expense', 'debit'),
        ('521002', 'Contractor Zakat', 'زكاة المتعهدين', 'expense', 'debit'),

        # التزامات تجاه الجهات الخارجية
        ('221001', 'Tax Authority Payable', 'ضريبة مستحقة للجهات الضريبية', 'liability', 'credit'),
        ('221002', 'Zakat Authority Payable', 'زكاة مستحقة', 'liability', 'credit'),
        ('221003', 'Insurance Company Payable', 'مستحقات شركات التأمين', 'liability', 'credit'),
    ]

    created_count = 0
    for code, name, name_ar, account_type, nature in labor_accounts:
        existing = Account.query.filter_by(code=code).first()
        if not existing:
            account = Account(
                code=code,
                name=name,
                name_ar=name_ar,
                account_type=account_type,
                nature=nature,
                opening_balance=0,
                is_active=True
            )
            db.session.add(account)
            created_count += 1

    if created_count > 0:
        db.session.commit()
        print(f"✅ تم إنشاء {created_count} حساب محاسبي لرواتب العمال")

    return created_count

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

    def can_delete(self):
        """التحقق من إمكانية حذف العقد"""
        # لا يمكن حذف العقد إذا كان له فواتير أو مدفوعات
        return len(self.invoices) == 0

    def has_financial_impact(self):
        """التحقق من وجود تأثير مالي"""
        return self.amount_received > 0

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
    paid_amount = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(50))
    payment_reference = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ربط القيد المحاسبي
    journal_entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=True)
    journal_entry = db.relationship('JournalEntry', foreign_keys=[journal_entry_id], backref='invoice')

    contract = db.relationship('Contract', backref='invoices')

    def has_journal_entry(self):
        """التحقق من وجود قيد محاسبي مرتبط"""
        return self.journal_entry_id is not None

    def can_delete(self):
        """التحقق من إمكانية حذف الفاتورة"""
        # لا يمكن حذف الفاتورة إذا:
        # 1. لها قيد محاسبي
        # 2. تم دفع جزء منها
        return not self.has_journal_entry() and self.paid_amount == 0

    def to_dict(self):
        return {
            'id': self.id,
            'contract_id': self.contract_id,
            'invoice_number': self.invoice_number,
            'amount': self.amount,
            'invoice_date': self.invoice_date.strftime('%Y-%m-%d') if self.invoice_date else None,
            'due_date': self.due_date.strftime('%Y-%m-%d') if self.due_date else None,
            'is_paid': self.is_paid,
            'paid_date': self.paid_date.strftime('%Y-%m-%d') if self.paid_date else None,
            'paid_amount': self.paid_amount,
            'remaining_amount': self.amount - self.paid_amount
        }
class EvaluationCriteria(db.Model):
    """معايير التقييم حسب الوظيفة"""
    __tablename__ = 'evaluation_criteria'

    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(100), nullable=False)  # 'عامل تسقية', 'عامل قص وتشكيل', 'مشرف', 'اداري'
    name = db.Column(db.String(200), nullable=False)  # اسم المعيار
    description = db.Column(db.Text)  # وصف المعيار
    min_score = db.Column(db.Integer, default=0)  # الحد الأدنى للدرجة
    max_score = db.Column(db.Integer, default=10)  # الحد الأقصى للدرجة
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)

    # العلاقات
    company = db.relationship('Company', foreign_keys=[company_id])

    def __repr__(self):
        return f"<EvaluationCriteria {self.job_title} - {self.name}>"


# ==================== Attendance Preparation Models (جديد) ====================

class AttendancePreparation(db.Model):
    """نموذج تحضير الدوام قبل احتساب الراتب"""
    __tablename__ = 'attendance_preparations'

    id = db.Column(db.Integer, primary_key=True)
    month_year = db.Column(db.String(20), nullable=False)  # MM-YYYY
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    preparation_date = db.Column(db.Date, default=datetime.utcnow().date)
    is_processed = db.Column(db.Boolean, default=False)  # هل تمت تصفيته وترحيله؟
    processed_date = db.Column(db.Date, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات
    company = db.relationship('Company', foreign_keys=[company_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    details = db.relationship('AttendancePreparationDetail', backref='preparation',
                              cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        return f'<AttendancePreparation {self.month_year} - {self.company_id or self.region}>'

    def to_dict(self):
        return {
            'id': self.id,
            'month_year': self.month_year,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'region': self.region,
            'preparation_date': self.preparation_date.strftime('%Y-%m-%d') if self.preparation_date else None,
            'is_processed': self.is_processed,
            'processed_date': self.processed_date.strftime('%Y-%m-%d') if self.processed_date else None,
            'total_employees': len(self.details),
            'locked_count': len([d for d in self.details if d.is_locked])
        }


class AttendancePreparationDetail(db.Model):
    """تفاصيل تحضير الدوام لكل موظف"""
    __tablename__ = 'attendance_preparation_details'

    id = db.Column(db.Integer, primary_key=True)
    preparation_id = db.Column(db.Integer, db.ForeignKey('attendance_preparations.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)

    # إحصائيات الدوام للشهر
    attendance_days = db.Column(db.Integer, default=0)  # أيام الحضور الفعلية
    absent_days = db.Column(db.Integer, default=0)  # أيام الغياب
    sick_days = db.Column(db.Integer, default=0)  # أيام الإجازة المرضية
    late_minutes_total = db.Column(db.Integer, default=0)  # إجمالي دقائق التأخير
    overtime_hours = db.Column(db.Float, default=0)  # ساعات العمل الإضافي
    daily_allowance = db.Column(db.Float, default=0)  # البدل اليومي (للساكن)

    # الحالة
    is_locked = db.Column(db.Boolean, default=False)  # هل تم قفل هذا الموظف للترحيل؟
    notes = db.Column(db.String(500))  # ملاحظات إضافية

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    employee = db.relationship('Employee')

    # فريد لكل موظف في نفس التحضير
    __table_args__ = (db.UniqueConstraint('preparation_id', 'employee_id', name='unique_prep_employee'),)

    def __repr__(self):
        return f'<AttendancePreparationDetail Prep:{self.preparation_id} Emp:{self.employee_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'preparation_id': self.preparation_id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'employee_code': self.employee.code if self.employee else None,
            'attendance_days': self.attendance_days,
            'absent_days': self.absent_days,
            'sick_days': self.sick_days,
            'late_minutes_total': self.late_minutes_total,
            'overtime_hours': self.overtime_hours,
            'daily_allowance': self.daily_allowance,
            'is_locked': self.is_locked,
            'notes': self.notes
        }

# ==================== نظام ترحيل فترات الرواتب المفصول ====================

class AttendancePeriodTransfer(db.Model):
    """نموذج ترحيل فترة دوام كاملة إلى الرواتب (مفصل حسب النوع)"""
    __tablename__ = 'attendance_period_transfers'

    PAYROLL_TYPES = {
        'admin': 'رواتب الإدارة',
        'labor': 'رواتب العمال'
    }

    id = db.Column(db.Integer, primary_key=True)
    period_name = db.Column(db.String(100), nullable=False)
    payroll_type = db.Column(db.String(20), nullable=False, default='admin')  # admin, labor
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    transfer_date = db.Column(db.Date, default=datetime.now().date)
    is_transferred = db.Column(db.Boolean, default=False)
    transferred_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # حقول الفلترة
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    region = db.Column(db.String(100), nullable=True)

    # إحصائيات الترحيل
    total_employees = db.Column(db.Integer, default=0)
    total_attendance_days = db.Column(db.Integer, default=0)
    total_salaries = db.Column(db.Float, default=0)
    total_deductions = db.Column(db.Float, default=0)
    total_net = db.Column(db.Float, default=0)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات
    transfers_details = db.relationship('AttendancePeriodTransferDetail', backref='transfer',
                                        cascade='all, delete-orphan', lazy=True)
    transferred_user = db.relationship('User', foreign_keys=[transferred_by])
    company = db.relationship('Company', foreign_keys=[company_id])

    __table_args__ = (
        db.UniqueConstraint('payroll_type', 'company_id', 'region', 'start_date', 'end_date',
                            name='unique_transfer_period'),
    )

    def get_payroll_type_name(self):
        """الحصول على اسم نوع الراتب"""
        return self.PAYROLL_TYPES.get(self.payroll_type, self.payroll_type)

    def check_overlap(self):
        """التحقق من وجود ترحيل مسبق لنفس الفترة والنوع"""
        query = AttendancePeriodTransfer.query.filter(
            AttendancePeriodTransfer.payroll_type == self.payroll_type,
            AttendancePeriodTransfer.start_date <= self.end_date,
            AttendancePeriodTransfer.end_date >= self.start_date,
            AttendancePeriodTransfer.id != self.id if self.id else True
        )

        # فلترة حسب الشركة أو المنطقة
        if self.company_id:
            query = query.filter(AttendancePeriodTransfer.company_id == self.company_id)
        elif self.region:
            query = query.filter(AttendancePeriodTransfer.region == self.region)
        else:
            query = query.filter(
                AttendancePeriodTransfer.company_id.is_(None),
                AttendancePeriodTransfer.region.is_(None)
            )

        return query.first() is not None

    def get_transfer_summary(self):
        """الحصول على ملخص الترحيل"""
        return {
            'period_name': self.period_name,
            'payroll_type': self.get_payroll_type_name(),
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'total_employees': self.total_employees,
            'total_attendance_days': self.total_attendance_days,
            'total_salaries': self.total_salaries,
            'total_deductions': self.total_deductions,
            'total_net': self.total_net,
            'is_transferred': self.is_transferred
        }

    def to_dict(self):
        return {
            'id': self.id,
            'period_name': self.period_name,
            'payroll_type': self.payroll_type,
            'payroll_type_name': self.get_payroll_type_name(),
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else None,
            'region': self.region,
            'total_employees': self.total_employees,
            'total_net': self.total_net,
            'is_transferred': self.is_transferred,
            'transfer_date': self.transfer_date.strftime('%Y-%m-%d') if self.transfer_date else None
        }


class AttendancePeriodTransferDetail(db.Model):
    """تفاصيل ترحيل فترة دوام لكل موظف (مفصل حسب نوع الموظف)"""
    __tablename__ = 'attendance_period_transfer_details'

    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('attendance_period_transfers.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    salary_id = db.Column(db.Integer, db.ForeignKey('salaries.id'), nullable=True)  # الراتب المرتبط

    # إحصائيات الدوام المستخرجة
    attendance_days = db.Column(db.Integer, default=0)
    absent_days = db.Column(db.Integer, default=0)
    sick_days = db.Column(db.Integer, default=0)
    late_minutes_total = db.Column(db.Integer, default=0)
    overtime_hours = db.Column(db.Float, default=0)
    daily_allowance = db.Column(db.Float, default=0)

    # المبالغ المالية
    base_salary = db.Column(db.Float, default=0)
    attendance_amount = db.Column(db.Float, default=0)
    overtime_amount = db.Column(db.Float, default=0)
    daily_allowance_amount = db.Column(db.Float, default=0)

    # الخصومات
    advance_amount = db.Column(db.Float, default=0)
    deduction_amount = db.Column(db.Float, default=0)
    penalty_amount = db.Column(db.Float, default=0)
    absence_deduction = db.Column(db.Float, default=0)

    # الإجمالي
    total_additions = db.Column(db.Float, default=0)
    total_deductions = db.Column(db.Float, default=0)
    final_amount = db.Column(db.Float, default=0)  # Admin: net_salary, Labor: net_amount

    # الحالة
    is_processed = db.Column(db.Boolean, default=False)
    processed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات
    employee = db.relationship('Employee', foreign_keys=[employee_id])
    salary = db.relationship('Salary', foreign_keys=[salary_id])

    __table_args__ = (db.UniqueConstraint('transfer_id', 'employee_id', name='unique_transfer_employee'),)

    def calculate_admin_salary(self, employee):
        """حساب راتب الإدارة"""
        # الراتب الأساسي للموظف
        self.base_salary = employee.salary or 0

        # عدد أيام الشهر
        days_in_month = 30

        # قيمة اليوم الواحد
        daily_rate = self.base_salary / days_in_month

        # مبلغ الحضور (الأيام الفعلية)
        self.attendance_amount = daily_rate * self.attendance_days

        # بدل التنقل (للساكنين فقط - حسب سياسة الشركة)
        if employee.is_resident:
            self.daily_allowance_amount = (employee.daily_allowance or 0) * self.attendance_days

        # ساعات الإضافي
        hourly_rate = daily_rate / 8
        self.overtime_amount = self.overtime_hours * (hourly_rate * 1.5)

        # خصم الغياب (مع مراعاة الإجازات المرضية)
        self.absence_deduction = daily_rate * self.absent_days

        # إجمالي الإضافات
        self.total_additions = self.attendance_amount + self.daily_allowance_amount + self.overtime_amount

        # إجمالي الخصومات
        self.total_deductions = self.absence_deduction + self.advance_amount + self.deduction_amount + self.penalty_amount

        # الراتب النهائي
        self.final_amount = self.total_additions - self.total_deductions

        return self.final_amount

    def calculate_labor_salary(self, employee):
        """حساب راتب العمال"""
        # نظام العمل (يومي/ساعي/قطاعي)
        work_type = getattr(employee, 'work_type', 'daily')

        if work_type == 'daily':
            # نظام يومي
            daily_wage = getattr(employee, 'daily_wage', 50)
            self.base_salary = daily_wage * self.attendance_days
            self.attendance_amount = self.base_salary

            # ساعات إضافية (بأجر يومي)
            hourly_rate = daily_wage / 8
            self.overtime_amount = self.overtime_hours * (hourly_rate * 1.5)

            # إضافة بدل تنقل للعمال (اختياري)
            self.daily_allowance_amount = getattr(employee, 'transportation_allowance', 0) * self.attendance_days

        elif work_type == 'hourly':
            # نظام ساعي
            hourly_rate = getattr(employee, 'hourly_rate', 10)
            self.attendance_amount = hourly_rate * (self.attendance_days * 8)  # 8 ساعات يومياً
            self.base_salary = self.attendance_amount
            self.overtime_amount = self.overtime_hours * (hourly_rate * 1.5)

        else:  # piece - نظام قطاعي
            piece_rate = getattr(employee, 'piece_rate', 0)
            pieces_count = getattr(employee, 'pieces_count', 0)
            self.attendance_amount = piece_rate * pieces_count
            self.base_salary = self.attendance_amount
            self.overtime_amount = 0

        # خصم الغياب
        daily_rate = (employee.daily_wage or 50) if hasattr(employee, 'daily_wage') else 50
        self.absence_deduction = daily_rate * self.absent_days

        # إجمالي الإضافات
        self.total_additions = self.attendance_amount + self.overtime_amount + self.daily_allowance_amount

        # إجمالي الخصومات
        self.total_deductions = self.absence_deduction + self.advance_amount + self.deduction_amount + self.penalty_amount

        # الراتب النهائي
        self.final_amount = self.total_additions - self.total_deductions

        return self.final_amount

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee.name if self.employee else None,
            'employee_code': self.employee.code if self.employee else None,
            'attendance_days': self.attendance_days,
            'absent_days': self.absent_days,
            'overtime_hours': self.overtime_hours,
            'base_salary': self.base_salary,
            'attendance_amount': self.attendance_amount,
            'overtime_amount': self.overtime_amount,
            'daily_allowance_amount': self.daily_allowance_amount,
            'advance_amount': self.advance_amount,
            'deduction_amount': self.deduction_amount,
            'penalty_amount': self.penalty_amount,
            'absence_deduction': self.absence_deduction,
            'final_amount': self.final_amount,
            'is_processed': self.is_processed
        }



# ==================== تحديث نموذج FinancialTransaction بإضافة الدوال ====================

def mark_as_settled(self, settlement_date=None):
    """تحديد المعاملة كمسواة (مرحلة إلى الراتب)"""
    self.is_settled = True
    self.settled_date = settlement_date or datetime.now().date()


def mark_as_unsettled(self):
    """إلغاء تسوية المعاملة"""
    self.is_settled = False
    self.settled_date = None


def can_be_settled(self):
    """التحقق من إمكانية تسوية المعاملة"""
    # يمكن تسوية المعاملة إذا لم تكن مسواة بالفعل
    return not self.is_settled


# إضافة الدوال إلى FinancialTransaction
FinancialTransaction.mark_as_settled = mark_as_settled
FinancialTransaction.mark_as_unsettled = mark_as_unsettled
FinancialTransaction.can_be_settled = can_be_settled

# ==================== إضافة دوال جديدة لنموذج Employee ====================

# أضف هذه الدوال إلى نموذج Employee الموجود
def get_attendance_summary(self, start_date, end_date):
    """الحصول على ملخص الحضور للموظف في فترة محددة"""
    attendances = Attendance.query.filter(
        Attendance.employee_id == self.id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    summary = {
        'attendance_days': 0,
        'absent_days': 0,
        'sick_days': 0,
        'late_minutes_total': 0,
    }

    for att in attendances:
        if att.attendance_status == 'present':
            summary['attendance_days'] += 1
        elif att.attendance_status == 'absent':
            summary['absent_days'] += 1
        elif att.attendance_status == 'sick':
            summary['sick_days'] += 1

        summary['late_minutes_total'] += att.late_minutes or 0

    return summary


def get_overtime_hours_in_period(self, start_date, end_date):
    """الحصول على ساعات العمل الإضافي في الفترة"""
    overtime_trans = FinancialTransaction.query.filter(
        FinancialTransaction.employee_id == self.id,
        FinancialTransaction.transaction_type == 'overtime',
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date,
        FinancialTransaction.is_settled == False
    ).all()

    total_hours = sum(t.amount for t in overtime_trans)
    return total_hours


def get_daily_allowance_amount(self, attendance_days):
    """حساب قيمة البدل اليومي"""
    if self.is_resident:
        # قيمة البدل اليومي من حقل daily_allowance
        return attendance_days * (self.daily_allowance or 500)
    return 0


# أضف هذه الدوال إلى نموذج Employee (ضعها داخل class Employee)
# يمكنك إضافتها بعد الدوال الموجودة مباشرة


# ==================== تحديث نموذج Salary بإضافة دوال جديدة ====================

# أضف هذه الدوال إلى نموذج Salary الموجود
def calculate_from_preparation(self, attendance_days, daily_allowance=0, overtime_hours=0):
    """حساب الراتب بناءً على تحضير الدوام"""
    self.attendance_days = attendance_days

    # حساب مبلغ الحضور (الراتب الأساسي مقسوم على 30 يوم × أيام الحضور)
    daily_rate = self.base_salary / 30
    self.attendance_amount = daily_rate * attendance_days

    # حساب البدل اليومي
    self.daily_allowance_amount = daily_allowance

    # حساب قيمة ساعات الإضافي (1.5 × الأجر العادي للساعة)
    hourly_rate = self.base_salary / 30 / 8
    self.overtime_amount = overtime_hours * (hourly_rate * 1.5)

    # إجمالي الإضافات
    total_additions = self.daily_allowance_amount + self.overtime_amount

    # إجمالي الخصومات (السلف + الخصومات + الجزاءات)
    total_deductions = self.advance_amount + self.deduction_amount + self.penalty_amount

    # الراتب النهائي
    self.total_salary = self.attendance_amount + total_additions - total_deductions

    return self.total_salary


def calculate_from_preparation_detail(self, preparation_detail):
    """حساب الراتب من تفاصيل تحضير الدوام"""
    return self.calculate_from_preparation(
        attendance_days=preparation_detail.attendance_days,
        daily_allowance=preparation_detail.daily_allowance,
        overtime_hours=preparation_detail.overtime_hours
    )


# ==================== إضافة دوال مساعدة لنموذج FinancialTransaction ====================

# أضف هذه الدوال إلى نموذج FinancialTransaction الموجود
def mark_as_settled(self, settlement_date=None):
    """تحديد المعاملة كمسواة (مرحلة إلى الراتب)"""
    self.is_settled = True
    self.settled_date = settlement_date or datetime.now().date()


def mark_as_unsettled(self):
    """إلغاء تسوية المعاملة"""
    self.is_settled = False
    self.settled_date = None


# ==================== تحديث دوال AttendancePreparation ====================

def add_methods_to_attendance_preparation():
    """إضافة دوال ديناميكية لنموذج AttendancePreparation"""

    def get_total_employees(self):
        return len(self.details)

    def get_locked_count(self):
        return len([d for d in self.details if d.is_locked])

    def get_unlocked_count(self):
        return len([d for d in self.details if not d.is_locked])

    def get_total_attendance_days(self):
        return sum(d.attendance_days for d in self.details)

    def get_total_overtime_hours(self):
        return sum(d.overtime_hours for d in self.details)

    def get_total_daily_allowance(self):
        return sum(d.daily_allowance for d in self.details)

    def is_ready_for_processing(self):
        """التحقق من جاهزية التحضير للترحيل"""
        return self.get_locked_count() == self.get_total_employees() and self.get_total_employees() > 0

    def process_to_salaries(self):
        """ترحيل التحضير إلى الرواتب"""
        from sqlalchemy.orm import joinedload

        if self.is_processed:
            raise ValueError("هذا التحضير تمت تصفيته مسبقاً")

        if not self.is_ready_for_processing():
            raise ValueError("لا يمكن الترحيل، بعض الموظفين غير مقفولين")

        salaries_created = []

        for detail in self.details:
            employee = detail.employee

            # البحث عن راتب موجود
            salary = Salary.query.filter_by(
                employee_id=employee.id,
                month_year=self.month_year
            ).first()

            if not salary:
                salary = Salary(
                    employee_id=employee.id,
                    month_year=self.month_year,
                    base_salary=employee.salary
                )
                db.session.add(salary)

            # حساب الراتب من تفاصيل التحضير
            salary.calculate_from_preparation_detail(detail)

            # ترحيل المعاملات المالية غير المسوّاة
            transactions = FinancialTransaction.query.filter_by(
                employee_id=employee.id,
                is_settled=False
            ).all()

            for trans in transactions:
                trans.mark_as_settled()

            salaries_created.append(salary)

        # تحديث حالة التحضير
        self.is_processed = True
        self.processed_date = datetime.now().date()

        return salaries_created

    # ربط الدوال بالنموذج
    AttendancePreparation.get_total_employees = get_total_employees
    AttendancePreparation.get_locked_count = get_locked_count
    AttendancePreparation.get_unlocked_count = get_unlocked_count
    AttendancePreparation.get_total_attendance_days = get_total_attendance_days
    AttendancePreparation.get_total_overtime_hours = get_total_overtime_hours
    AttendancePreparation.get_total_daily_allowance = get_total_daily_allowance
    AttendancePreparation.is_ready_for_processing = is_ready_for_processing
    AttendancePreparation.process_to_salaries = process_to_salaries


# استدعاء الدالة لإضافة الدوال
add_methods_to_attendance_preparation()


# ==================== تحديث دوال AttendancePreparationDetail ====================

def add_methods_to_attendance_preparation_detail():
    """إضافة دوال ديناميكية لنموذج AttendancePreparationDetail"""

    def lock(self):
        """قفل تفاصيل الموظف"""
        self.is_locked = True

    def unlock(self):
        """فتح تفاصيل الموظف"""
        self.is_locked = False

    def recalculate_from_attendance(self, start_date, end_date):
        """إعادة حساب الإحصائيات من سجلات الحضور"""
        summary = self.employee.get_attendance_summary(start_date, end_date)
        self.attendance_days = summary['attendance_days']
        self.absent_days = summary['absent_days']
        self.sick_days = summary['sick_days']
        self.late_minutes_total = summary['late_minutes_total']
        self.overtime_hours = self.employee.get_overtime_hours_in_period(start_date, end_date)
        self.daily_allowance = self.employee.get_daily_allowance_amount(self.attendance_days)

    AttendancePreparationDetail.lock = lock
    AttendancePreparationDetail.unlock = unlock
    AttendancePreparationDetail.recalculate_from_attendance = recalculate_from_attendance


# استدعاء الدالة لإضافة الدوال
add_methods_to_attendance_preparation_detail()


# ==================== تقييم المناطق والمواقع ====================

class AreaEvaluation(db.Model):
    """نموذج تقييم المناطق والمواقع (بدون علاقة بالعمال)"""
    __tablename__ = 'area_evaluations'

    id = db.Column(db.Integer, primary_key=True)
    evaluation_type = db.Column(db.String(50), nullable=False)  # region, location
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)

    # بيانات التقييم
    evaluation_date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    overall_score = db.Column(db.Float, default=0)
    comments = db.Column(db.Text)

    # الحالة
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    is_active = db.Column(db.Boolean, default=True)

    # معايير التقييم (مخزنة كـ JSON)
    criteria_scores = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    region = db.relationship('Region', foreign_keys=[region_id])
    location = db.relationship('Location', foreign_keys=[location_id])
    evaluator = db.relationship('User', foreign_keys=[evaluator_id])

    def set_criteria_scores(self, scores_list):
        """تخزين درجات المعايير"""
        import json
        self.criteria_scores = json.dumps(scores_list)

    def get_criteria_scores(self):
        """استرجاع درجات المعايير"""
        import json
        return json.loads(self.criteria_scores) if self.criteria_scores else []

    def get_rating(self):
        """الحصول على التقييم النهائي"""
        if self.overall_score >= 9:
            return 'ممتاز', 'success'
        elif self.overall_score >= 7:
            return 'جيد جداً', 'primary'
        elif self.overall_score >= 5:
            return 'جيد', 'info'
        elif self.overall_score >= 3:
            return 'مقبول', 'warning'
        else:
            return 'ضعيف', 'danger'

    def get_type_display(self):
        """عرض نوع التقييم"""
        return 'منطقة' if self.evaluation_type == 'region' else 'موقع'

    def get_name(self):
        """الحصول على اسم المنطقة/الموقع"""
        if self.evaluation_type == 'region' and self.region:
            return self.region.name
        elif self.location:
            return self.location.name
        return '-'


class AreaEvaluationCriteria(db.Model):
    """معايير تقييم المناطق والمواقع"""
    __tablename__ = 'area_evaluation_criteria'

    id = db.Column(db.Integer, primary_key=True)
    evaluation_type = db.Column(db.String(50), nullable=False)  # region, location
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    weight = db.Column(db.Float, default=1.0)  # وزن المعيار
    max_score = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)  # ترتيب العرض
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AreaEvaluationCriteria {self.evaluation_type} - {self.name}>"


# ==================== نظام الحسابات المحاسبي ====================

class Account(db.Model):
    """نموذج الحسابات المحاسبي (دليل الحسابات)"""
    __tablename__ = 'accounts'

    # أنواع الحسابات
    ACCOUNT_TYPES = {
        'asset': 'أصول',
        'liability': 'خصوم',
        'equity': 'حقوق ملكية',
        'revenue': 'إيرادات',
        'expense': 'مصروفات',
        'cost': 'تكاليف'
    }

    # طبيعة الحساب
    NATURE = {
        'debit': 'مدين',
        'credit': 'دائن'
    }

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # رقم الحساب (مثال: 100001)
    name = db.Column(db.String(100), nullable=False)  # اسم الحساب
    name_ar = db.Column(db.String(100), nullable=False)  # الاسم بالعربية
    account_type = db.Column(db.String(20), nullable=False)  # نوع الحساب
    nature = db.Column(db.String(10), nullable=False)  # طبيعة الحساب (debit/credit)
    parent_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)  # الحساب الأب
    level = db.Column(db.Integer, default=1)  # مستوى الحساب
    is_active = db.Column(db.Boolean, default=True)
    opening_balance = db.Column(db.Float, default=0)  # الرصيد الافتتاحي
    opening_balance_date = db.Column(db.Date)  # تاريخ الرصيد الافتتاحي
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    parent = db.relationship('Account', remote_side=[id], backref='children')
    journal_entries = db.relationship('JournalEntryDetail', backref='account')

    def get_balance(self, as_of_date=None):
        """الحصول على رصيد الحساب حتى تاريخ معين"""
        from sqlalchemy import func

        query = db.session.query(func.sum(JournalEntryDetail.debit), func.sum(JournalEntryDetail.credit))

        if as_of_date:
            query = query.join(JournalEntry).filter(JournalEntry.date <= as_of_date)

        result = query.filter(JournalEntryDetail.account_id == self.id).first()

        total_debit = result[0] or 0
        total_credit = result[1] or 0

        if self.nature == 'debit':
            balance = self.opening_balance + total_debit - total_credit
        else:
            balance = self.opening_balance + total_credit - total_debit

        return balance

    def get_type_name(self):
        return self.ACCOUNT_TYPES.get(self.account_type, self.account_type)

    def get_nature_name(self):
        return self.NATURE.get(self.nature, self.nature)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'name_ar': self.name_ar,
            'account_type': self.account_type,
            'account_type_name': self.get_type_name(),
            'nature': self.nature,
            'nature_name': self.get_nature_name(),
            'parent_id': self.parent_id,
            'level': self.level,
            'is_active': self.is_active,
            'opening_balance': self.opening_balance,
            'balance': self.get_balance()
        }


class JournalEntry(db.Model):
    """نموذج القيد اليومي"""
    __tablename__ = 'journal_entries'

    id = db.Column(db.Integer, primary_key=True)
    entry_number = db.Column(db.String(50), unique=True, nullable=False)  # رقم القيد
    date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    description = db.Column(db.String(500), nullable=False)  # وصف القيد
    reference_type = db.Column(db.String(50), nullable=True)  # نوع المرجع (salary, transaction, invoice, etc.)
    reference_id = db.Column(db.Integer, nullable=True)  # معرف المرجع
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_posted = db.Column(db.Boolean, default=True)  # هل تم ترحيل القيد
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    creator = db.relationship('User', foreign_keys=[created_by])
    details = db.relationship('JournalEntryDetail', backref='entry', cascade='all, delete-orphan')

    def get_total_debit(self):
        return sum(d.debit for d in self.details) or 0

    def get_total_credit(self):
        return sum(d.credit for d in self.details) or 0

    def is_balanced(self):
        """التحقق من توازن القيد (مجموع المدين = مجموع الدائن)"""
        return abs(self.get_total_debit() - self.get_total_credit()) < 0.01

    def to_dict(self):
        return {
            'id': self.id,
            'entry_number': self.entry_number,
            'date': self.date.strftime('%Y-%m-%d'),
            'description': self.description,
            'total_debit': self.get_total_debit(),
            'total_credit': self.get_total_credit(),
            'is_balanced': self.is_balanced(),
            'details': [d.to_dict() for d in self.details]
        }


class JournalEntryDetail(db.Model):
    """تفاصيل القيد اليومي (مدين/دائن)"""
    __tablename__ = 'journal_entry_details'

    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    debit = db.Column(db.Float, default=0)  # مدين
    credit = db.Column(db.Float, default=0)  # دائن
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'account_code': self.account.code if self.account else None,
            'account_name': self.account.name if self.account else None,
            'debit': self.debit,
            'credit': self.credit,
            'description': self.description
        }


class AccountBalance(db.Model):
    """نموذج أرصدة الحسابات (للأداء السريع)"""
    __tablename__ = 'account_balances'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    fiscal_year = db.Column(db.Integer, nullable=False)  # السنة المالية
    period = db.Column(db.Integer, nullable=False)  # الفترة (شهر)
    opening_balance = db.Column(db.Float, default=0)
    debit = db.Column(db.Float, default=0)
    credit = db.Column(db.Float, default=0)
    closing_balance = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    account = db.relationship('Account', backref='balances')

    __table_args__ = (db.UniqueConstraint('account_id', 'fiscal_year', 'period', name='unique_account_period'),)


class FiscalYear(db.Model):
    """نموذج السنة المالية"""
    __tablename__ = 'fiscal_years'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_closed = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FiscalYear {self.name}>"


class TrialBalance(db.Model):
    """نموذج ميزان المراجعة"""
    __tablename__ = 'trial_balances'

    id = db.Column(db.Integer, primary_key=True)
    as_of_date = db.Column(db.Date, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    opening_balance = db.Column(db.Float, default=0)
    debit = db.Column(db.Float, default=0)
    credit = db.Column(db.Float, default=0)
    closing_balance = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # العلاقات
    account = db.relationship('Account', backref='trial_balances')


# ==================== مدفوعات الشركات (من طلعت هائل إلى الشركات) ====================

class CompanyPayment(db.Model):
    """مدفوعات من طلعت هائل إلى الشركات"""
    __tablename__ = 'company_payments'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)  # الفاتورة المرتبطة
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))  # cash, bank_transfer, check
    reference_number = db.Column(db.String(100))  # رقم المرجع
    notes = db.Column(db.Text)

    # الحالة
    is_posted_to_accounts = db.Column(db.Boolean, default=False)  # هل تم ترحيله للحسابات

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # العلاقات
    company = db.relationship('Company', backref='payments')
    invoice = db.relationship('Invoice', backref='payments')
    creator = db.relationship('User', foreign_keys=[created_by])

    def __repr__(self):
        return f"<CompanyPayment {self.company.name} - {self.amount}>"


# ==================== إدارة الموردين والفواتير (موحدة - نسخة مبسطة) ====================

class Supplier(db.Model):
    """نموذج الموردين"""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    name_ar = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.String(300))
    tax_number = db.Column(db.String(50))
    bank_name = db.Column(db.String(100))
    bank_account = db.Column(db.String(100))
    notes = db.Column(db.Text)
    supplier_type = db.Column(db.String(50), default='general')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # علاقة مبسطة - بدون backref معقد
    def get_type_display(self):
        types = {
            'utility': 'كهرباء وماء',
            'rent': 'إيجار',
            'office': 'مكتبية',
            'equipment': 'معدات وأدوات',
            'general': 'عام'
        }
        return types.get(self.supplier_type, self.supplier_type)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_ar': self.name_ar,
            'phone': self.phone,
            'supplier_type': self.supplier_type,
            'is_active': self.is_active
        }


class ExpenseCategory(db.Model):
    """نموذج فئات المصروفات"""
    __tablename__ = 'expense_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id'), nullable=True)
    account_code = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship('ExpenseCategory', remote_side=[id], backref='children')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_ar': self.name_ar,
            'account_code': self.account_code
        }


class SupplierInvoice(db.Model):
    """نموذج فواتير الموردين (موحدة)"""
    __tablename__ = 'supplier_invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)

    # مبالغ الدفع
    paid_amount = db.Column(db.Float, default=0)
    remaining_amount = db.Column(db.Float, default=0)

    # الحالة
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    reference_number = db.Column(db.String(100))
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    document_path = db.Column(db.String(500))

    # المحاسبة
    is_posted_to_accounts = db.Column(db.Boolean, default=False)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # علاقات مبسطة
    supplier = db.relationship('Supplier', foreign_keys=[supplier_id])
    category = db.relationship('ExpenseCategory', foreign_keys=[category_id])
    creator = db.relationship('User', foreign_keys=[created_by])

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'supplier_name': self.supplier.name_ar if self.supplier else '',
            'category_name': self.category.name_ar if self.category else '',
            'amount': self.amount,
            'paid_amount': self.paid_amount,
            'remaining_amount': self.remaining_amount,
            'status': self.status,
            'invoice_date': self.invoice_date.strftime('%Y-%m-%d') if self.invoice_date else ''
        }

    def can_delete(self):
        """التحقق من إمكانية حذف فاتورة المورد"""
        # لا يمكن حذف الفاتورة إذا تم دفع جزء منها
        return self.paid_amount == 0

    def has_financial_impact(self):
        """التحقق من وجود تأثير مالي"""
        return self.paid_amount > 0




class SupplierInvoicePayment(db.Model):
    """نموذج مدفوعات فواتير الموردين"""
    __tablename__ = 'supplier_invoice_payments'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('supplier_invoices.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    is_posted_to_accounts = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by])
    invoice = db.relationship('SupplierInvoice', foreign_keys=[invoice_id])

