from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
from models import (
    db, User, Employee, Attendance, Company, Region, Location,
    Evaluation, EvaluationCriteria, EvaluationDetail, FinancialTransaction, Salary,
    Contract, Supplier, SupplierInvoice, SupplierInvoicePayment, Invoice, Account, JournalEntry, JournalEntryDetail,
    JournalEntryDetail as JED, MealDeduction, LaborMonthlyCost, ContractorAnnualCost,
    ExpenseCategory, SystemSettings, AllowanceSetting, WorkPlan, WorkPlanTask,
    FinancialPeriod, LeaveType, LeaveBalance, LeaveRequest, BankInfo
)

rest_api = Blueprint('rest_api', __name__, url_prefix='/api')


def ok(data=None, message='success'):
    return jsonify({'success': True, 'message': message, 'data': data})


def fail(message='error', status=400):
    return jsonify({'success': False, 'message': message}), status


def check_duplicate_journal_entry(reference_type, reference_id):
    """التحقق من عدم وجود قيد مكرر لنفس العملية"""
    existing = JournalEntry.query.filter_by(reference_type=reference_type, reference_id=reference_id).first()
    return existing is not None


def fail(message='error', status=400):
    return jsonify({'success': False, 'message': message}), status


# ==================== AUTH ====================

@rest_api.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return fail('يرجى إدخال اسم المستخدم وكلمة المرور')

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return fail('اسم المستخدم أو كلمة المرور غير صحيحة', 401)

    login_user(user, remember=True)
    return ok({'user': user.to_dict()}, 'تم تسجيل الدخول بنجاح')

@rest_api.route('/debug/session')
def api_debug_session():
    from flask_login import current_user
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'user_id': getattr(current_user, 'id', None),
        'session_cookie': bool(request.cookies.get('session')),
    })


@rest_api.route('/auth/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return ok(message='تم تسجيل الخروج بنجاح')


@rest_api.route('/auth/me')
@login_required
def api_me():
    return ok(current_user.to_dict())


# ==================== EMPLOYEES ====================

@rest_api.route('/employees')
@login_required
def api_employees_list():
    q = Employee.query
    company_id = request.args.get('company_id')
    region = request.args.get('region')
    is_active = request.args.get('is_active')

    if company_id:
        q = q.filter_by(company_id=int(company_id))
    if region:
        q = q.filter_by(region=region)
    if is_active is not None:
        q = q.filter_by(is_active=is_active.lower() == 'true')

    if current_user.role == 'supervisor' and current_user.company_id:
        q = q.filter_by(company_id=current_user.company_id)

    employees = q.order_by(Employee.name).all()
    return ok([emp.to_dict() for emp in employees])


@rest_api.route('/employees/<int:emp_id>')
@login_required
def api_employee_get(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    return ok(emp.to_dict())


@rest_api.route('/employees', methods=['POST'])
@login_required
def api_employee_create():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get('card_number'):
        return fail('رقم البطاقة مطلوب')
    if not data.get('code'):
        data['code'] = data.get('card_number', '')
    emp = Employee(
        name=data.get('name', ''),
        card_number=data.get('card_number', ''),
        code=data.get('code', '') or data.get('card_number', ''),
        job_title=data.get('job_title', ''),
        phone=data.get('phone', ''),
        company_id=data.get('company_id'),
        region=data.get('region', ''),
        region_id=data.get('region_id'),
        salary=data.get('salary', 0),
        total_salary=data.get('total_salary', 0),
        basic_salary=data.get('basic_salary', 0),
        daily_allowance=data.get('daily_allowance', 0),
        clothing_allowance=data.get('clothing_allowance', 0),
        health_card_allowance=data.get('health_card_allowance', 0),
        monthly_insurance=data.get('monthly_insurance', 0),
        is_active=data.get('is_active', True),
        is_resident=data.get('is_resident', False),
        employee_type=data.get('employee_type', 'worker'),
        worker_type=data.get('worker_type', 'permanent'),
        supervisor_id=data.get('supervisor_id'),
    )
    db.session.add(emp)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return fail('رقم البطاقة أو الكود مسجل بالفعل', 400)
    return ok(emp.to_dict(), 'تم إضافة الموظف بنجاح')


@rest_api.route('/employees/<int:emp_id>', methods=['PUT'])
@login_required
def api_employee_update(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    data = request.get_json(force=True, silent=True) or {}
    for field in ['name', 'card_number', 'code', 'job_title', 'phone',
                  'company_id', 'region', 'region_id', 'salary', 'total_salary',
                  'basic_salary', 'daily_allowance', 'clothing_allowance',
                  'health_card_allowance', 'monthly_insurance',
                  'is_active', 'is_resident', 'employee_type', 'worker_type',
                  'supervisor_id']:
        if field in data:
            setattr(emp, field, data[field])
    db.session.commit()
    return ok(emp.to_dict(), 'تم تحديث الموظف بنجاح')


@rest_api.route('/employees/<int:emp_id>', methods=['DELETE'])
@login_required
def api_employee_delete(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    # فحص الارتباط بسجلات أخرى
    has_salaries = Salary.query.filter_by(employee_id=emp_id).first()
    if has_salaries:
        return fail('لا يمكن حذف الموظف لأنه مرتبط بسجلات رواتب', 400)
    has_attendance = Attendance.query.filter_by(employee_id=emp_id).first()
    if has_attendance:
        return fail('لا يمكن حذف الموظف لأنه مرتبط بسجلات حضور', 400)
    has_transactions = FinancialTransaction.query.filter_by(employee_id=emp_id).first()
    if has_transactions:
        return fail('لا يمكن حذف الموظف لأنه مرتبط بمعاملات مالية', 400)
    db.session.delete(emp)
    db.session.commit()
    return ok(message='تم حذف الموظف بنجاح')


@rest_api.route('/employees/check_card')
@login_required
def api_check_card():
    card = request.args.get('card_number')
    emp_id = request.args.get('exclude_id')
    q = Employee.query.filter_by(card_number=card)
    if emp_id:
        q = q.filter(Employee.id != int(emp_id))
    return ok({'exists': q.first() is not None})


# ==================== BANK INFO ====================

@rest_api.route('/employees/<int:emp_id>/bank-info')
@login_required
def api_bank_info_list(emp_id):
    items = BankInfo.query.filter_by(employee_id=emp_id).order_by(BankInfo.is_primary.desc(), BankInfo.id).all()
    return ok([i.to_dict() for i in items])


@rest_api.route('/employees/<int:emp_id>/bank-info', methods=['POST'])
@login_required
def api_bank_info_create(emp_id):
    data = request.get_json(force=True, silent=True) or {}
    if not data.get('bank_name') or not data.get('account_number'):
        return fail('اسم البنك ورقم الحساب مطلوبان')
    if data.get('is_primary'):
        BankInfo.query.filter_by(employee_id=emp_id).update({'is_primary': False})
    item = BankInfo(employee_id=emp_id, bank_name=data['bank_name'], account_number=data['account_number'],
                    iban=data.get('iban', ''), swift_code=data.get('swift_code', ''),
                    branch_name=data.get('branch_name', ''), account_type=data.get('account_type', 'current'),
                    currency=data.get('currency', 'YER'), is_primary=data.get('is_primary', True),
                    notes=data.get('notes', ''))
    db.session.add(item)
    db.session.commit()
    return ok(item.to_dict(), 'تمت الإضافة بنجاح')


@rest_api.route('/bank-info/<int:item_id>', methods=['PUT'])
@login_required
def api_bank_info_update(item_id):
    item = BankInfo.query.get_or_404(item_id)
    data = request.get_json(force=True, silent=True) or {}
    if data.get('is_primary'):
        BankInfo.query.filter_by(employee_id=item.employee_id).update({'is_primary': False})
    for field in ['bank_name', 'account_number', 'iban', 'swift_code', 'branch_name', 'account_type', 'currency', 'is_primary', 'notes']:
        if field in data:
            setattr(item, field, data[field])
    item.updated_at = datetime.utcnow()
    db.session.commit()
    return ok(item.to_dict(), 'تم التعديل بنجاح')


@rest_api.route('/bank-info/<int:item_id>', methods=['DELETE'])
@login_required
def api_bank_info_delete(item_id):
    item = BankInfo.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return ok(message='تم الحذف بنجاح')


# ==================== ATTENDANCE ====================

@rest_api.route('/attendance')
@login_required
def api_attendance_list():
    q = Attendance.query
    date_str = request.args.get('date')
    emp_id = request.args.get('employee_id')

    if date_str:
        q = q.filter_by(date=datetime.strptime(date_str, '%Y-%m-%d').date())
    if emp_id:
        q = q.filter_by(employee_id=int(emp_id))

    records = q.order_by(Attendance.date.desc()).limit(200).all()
    return ok([{
        'id': r.id,
        'employee_id': r.employee_id,
        'employee_name': r.employee.name if r.employee else '',
        'date': r.date.strftime('%Y-%m-%d') if r.date else '',
        'check_in_time': r.check_in_time.strftime('%H:%M') if r.check_in_time else None,
        'check_out_time': r.check_out_time.strftime('%H:%M') if r.check_out_time else None,
        'attendance_status': r.attendance_status,
        'notes': r.notes or '',
    } for r in records])


@rest_api.route('/attendance', methods=['POST'])
@login_required
def api_attendance_add():
    data = request.get_json(force=True, silent=True) or {}
    rec = Attendance(
        employee_id=data.get('employee_id'),
        date=datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else datetime.now().date(),
        attendance_status=data.get('attendance_status', 'present'),
        notes=data.get('notes', ''),
    )
    if data.get('time_in'):
        rec.check_in_time = datetime.strptime(data['time_in'], '%H:%M').time()
    if data.get('time_out'):
        rec.check_out_time = datetime.strptime(data['time_out'], '%H:%M').time()
    db.session.add(rec)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return fail('يوجد سجل حضور مسجل بالفعل لهذا الموظف في نفس التاريخ', 400)
    return ok({'id': rec.id}, 'تم إضافة سجل الحضور')


@rest_api.route('/attendance/<int:rec_id>', methods=['PUT'])
@login_required
def api_attendance_update(rec_id):
    rec = Attendance.query.get_or_404(rec_id)
    data = request.get_json(force=True, silent=True) or {}
    for field in ['attendance_status', 'notes']:
        if field in data:
            setattr(rec, field, data[field])
    if 'time_in' in data and data['time_in']:
        rec.check_in_time = datetime.strptime(data['time_in'], '%H:%M').time()
    if 'time_out' in data and data['time_out']:
        rec.check_out_time = datetime.strptime(data['time_out'], '%H:%M').time()
    db.session.commit()
    return ok(message='تم تحديث سجل الحضور')


@rest_api.route('/attendance/<int:rec_id>', methods=['DELETE'])
@login_required
def api_attendance_delete(rec_id):
    rec = Attendance.query.get_or_404(rec_id)
    db.session.delete(rec)
    db.session.commit()
    return ok(message='تم حذف سجل الحضور')


@rest_api.route('/attendance/bulk', methods=['POST'])
@login_required
def api_attendance_bulk():
    data = request.get_json(force=True, silent=True) or {}
    date_str = data.get('date')
    records = data.get('records', [])

    if not date_str:
        return fail('التاريخ مطلوب', 400)
    if not records:
        return fail('لا توجد سجلات للحفظ', 400)

    att_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    created = 0
    skipped = 0
    for rec in records:
        emp_id = rec.get('employee_id')
        status = rec.get('attendance_status', 'absent')
        if not emp_id:
            continue
        existing = Attendance.query.filter_by(employee_id=emp_id, date=att_date).first()
        if existing:
            existing.attendance_status = status
            existing.notes = rec.get('notes', '')
            if rec.get('time_in'):
                existing.check_in_time = datetime.strptime(rec['time_in'], '%H:%M').time()
            if rec.get('time_out'):
                existing.check_out_time = datetime.strptime(rec['time_out'], '%H:%M').time()
        else:
            new_rec = Attendance(
                employee_id=emp_id,
                date=att_date,
                attendance_status=status,
                notes=rec.get('notes', ''),
                attendance_type='group',
            )
            if rec.get('time_in'):
                new_rec.check_in_time = datetime.strptime(rec['time_in'], '%H:%M').time()
            if rec.get('time_out'):
                new_rec.check_out_time = datetime.strptime(rec['time_out'], '%H:%M').time()
            db.session.add(new_rec)
            created += 1

    db.session.commit()
    return ok({'created': created, 'total': len(records)}, f'تم حفظ حضور {created} موظف')


# ==================== COMPANIES ====================

@rest_api.route('/companies')
@login_required
def api_companies_list():
    companies = Company.query.order_by(Company.name).all()
    return ok([{
        'id': c.id,
        'name': c.name,
        'contact_person': c.contact_person or '',
        'phone': c.phone or '',
        'email': c.email or '',
        'employees_count': Employee.query.filter_by(company_id=c.id, is_active=True).count(),
        'is_active': True,
    } for c in companies])


@rest_api.route('/companies/<int:cid>')
@login_required
def api_company_get(cid):
    c = Company.query.get_or_404(cid)
    return ok({
        'id': c.id,
        'name': c.name,
        'contact_person': c.contact_person or '',
        'phone': c.phone or '',
        'email': c.email or '',
        'is_active': True,
    })


@rest_api.route('/companies', methods=['POST'])
@login_required
def api_company_create():
    data = request.get_json(force=True, silent=True) or {}
    c = Company(
        name=data.get('name', ''),
        contact_person=data.get('contact_person', ''),
        phone=data.get('phone', ''),
        email=data.get('email', ''),
    )
    db.session.add(c)
    db.session.commit()
    return ok({'id': c.id}, 'تم إضافة الشركة بنجاح')


@rest_api.route('/companies/<int:cid>', methods=['PUT'])
@login_required
def api_company_update(cid):
    c = Company.query.get_or_404(cid)
    data = request.get_json(force=True, silent=True) or {}
    for field in ['name', 'contact_person', 'phone', 'email']:
        if field in data:
            setattr(c, field, data[field])
    db.session.commit()
    return ok(message='تم تحديث الشركة')


@rest_api.route('/companies/<int:cid>', methods=['DELETE'])
@login_required
def api_company_delete(cid):
    c = Company.query.get_or_404(cid)
    # فحص الارتباط بسجلات أخرى
    has_contracts = Contract.query.filter_by(company_id=cid).first()
    if has_contracts:
        return fail('لا يمكن حذف الشركة لأنها مرتبط بعقود', 400)
    has_employees = Employee.query.filter_by(company_id=cid).first()
    if has_employees:
        return fail('لا يمكن حذف الشركة لأنها مرتبط بموظفين', 400)
    has_invoices = Invoice.query.join(Contract).filter(Contract.company_id == cid).first()
    if has_invoices:
        return fail('لا يمكن حذف الشركة لأنها مرتبط بفواتير', 400)
    db.session.delete(c)
    db.session.commit()
    return ok(message='تم حذف الشركة')


@rest_api.route('/companies/<int:cid>/regions')
@login_required
def api_company_regions(cid):
    regions = Region.query.filter_by(company_id=cid).all()
    return ok([{'id': r.id, 'name': r.name} for r in regions])


@rest_api.route('/regions/<int:rid>/locations')
@login_required
def api_region_locations(rid):
    locations = Location.query.filter_by(region_id=rid).all()
    return ok([{'id': l.id, 'name': l.name} for l in locations])


# ==================== EVALUATIONS ====================

@rest_api.route('/evaluations')
@login_required
def api_evaluations_list():
    q = Evaluation.query
    emp_id = request.args.get('employee_id')
    if emp_id:
        q = q.filter_by(employee_id=int(emp_id))
    evaluations = q.order_by(Evaluation.date.desc()).limit(200).all()
    return ok([{
        'id': e.id,
        'employee_id': e.employee_id,
        'employee_name': e.employee.name if e.employee else '',
        'employee_job': e.employee.job_title if e.employee else '',
        'evaluation_type': e.evaluation_type,
        'evaluator_name': e.evaluator.full_name if e.evaluator else '',
        'date': e.date.strftime('%Y-%m-%d') if e.date else '',
        'score': e.score,
        'rating': e.get_rating(),
        'comments': e.comments or '',
        'region_id': e.region_id,
        'region_name': e.region.name if e.region else None,
        'location_id': e.location_id,
        'location_name': e.location.name if e.location else None,
        'details': [d.to_dict() for d in e.details],
    } for e in evaluations])


@rest_api.route('/evaluations', methods=['POST'])
@login_required
def api_evaluation_create():
    data = request.get_json(force=True, silent=True) or {}
    e = Evaluation(
        employee_id=data.get('employee_id'),
        evaluator_id=current_user.id,
        evaluation_type=data.get('evaluation_type', 'supervisor'),
        date=datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else datetime.now().date(),
        score=data.get('score', 0),
        comments=data.get('comments', ''),
        region_id=data.get('region_id'),
        location_id=data.get('location_id'),
    )
    db.session.add(e)
    db.session.flush()

    criteria_scores = data.get('criteria', [])
    total = 0
    count = 0
    for cs in criteria_scores:
        detail = EvaluationDetail(
            evaluation_id=e.id,
            criterion_id=cs['criterion_id'],
            score=cs.get('score', 0),
            notes=cs.get('notes', ''),
        )
        db.session.add(detail)
        total += cs.get('score', 0)
        count += 1

    if count > 0 and not data.get('score'):
        e.score = round(total / count * 20)

    db.session.commit()
    return ok({'id': e.id}, 'تم إضافة التقييم')


@rest_api.route('/evaluations/<int:eid>', methods=['DELETE'])
@login_required
def api_evaluation_delete(eid):
    e = Evaluation.query.get_or_404(eid)
    EvaluationDetail.query.filter_by(evaluation_id=eid).delete()
    db.session.delete(e)
    db.session.commit()
    return ok(message='تم حذف التقييم')


@rest_api.route('/evaluations/areas')
@login_required
def api_evaluation_areas():
    regions = Region.query.all()
    return ok([{'id': r.id, 'name': r.name, 'company_id': r.company_id} for r in regions])


@rest_api.route('/evaluation-criteria')
@login_required
def api_evaluation_criteria():
    job_title = request.args.get('job_title', '')
    q = EvaluationCriteria.query.filter_by(is_active=True)
    if job_title:
        q = q.filter_by(job_title=job_title)
    criteria = q.all()
    return ok([c.to_dict() for c in criteria])


@rest_api.route('/evaluation-criteria', methods=['POST'])
@login_required
def api_evaluation_criteria_create():
    data = request.get_json(force=True, silent=True) or {}
    c = EvaluationCriteria(
        job_title=data.get('job_title', ''),
        name=data.get('name', ''),
        description=data.get('description', ''),
        max_score=data.get('max_score', 5),
        company_id=data.get('company_id'),
    )
    db.session.add(c)
    db.session.commit()
    return ok({'id': c.id}, 'تم إضافة المعيار')


@rest_api.route('/evaluation-criteria/<int:cid>', methods=['DELETE'])
@login_required
def api_evaluation_criteria_delete(cid):
    c = EvaluationCriteria.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    return ok(message='تم حذف المعيار')


@rest_api.route('/evaluation-criteria/<int:cid>', methods=['PUT'])
@login_required
def api_evaluation_criteria_update(cid):
    c = EvaluationCriteria.query.get_or_404(cid)
    data = request.get_json(force=True, silent=True) or {}
    if 'job_title' in data:
        c.job_title = data['job_title']
    if 'name' in data:
        c.name = data['name']
    if 'description' in data:
        c.description = data['description']
    if 'max_score' in data:
        c.max_score = data['max_score']
    db.session.commit()
    return ok(message='تم تعديل المعيار')


@rest_api.route('/evaluation-criteria/job-titles')
@login_required
def api_evaluation_job_titles():
    titles = db.session.query(EvaluationCriteria.job_title).distinct().all()
    return ok([t[0] for t in titles if t[0]])


# ==================== REGIONS & LOCATIONS ====================

@rest_api.route('/regions')
@login_required
def api_regions_list():
    regions = Region.query.all()
    return ok([r.to_dict() for r in regions])


@rest_api.route('/regions', methods=['POST'])
@login_required
def api_region_create():
    data = request.get_json(force=True, silent=True) or {}
    r = Region(name=data.get('name', ''), company_id=data.get('company_id'))
    db.session.add(r)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return fail('المنطقة موجودة بالفعل لهذه الشركة', 400)
    return ok({'id': r.id}, 'تم إضافة المنطقة')


@rest_api.route('/regions/<int:rid>', methods=['DELETE'])
@login_required
def api_region_delete(rid):
    r = Region.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    return ok(message='تم حذف المنطقة')


@rest_api.route('/locations')
@login_required
def api_locations_list():
    region_id = request.args.get('region_id')
    q = Location.query
    if region_id:
        q = q.filter_by(region_id=int(region_id))
    return ok([l.to_dict() for l in q.all()])


@rest_api.route('/locations', methods=['POST'])
@login_required
def api_location_create():
    data = request.get_json(force=True, silent=True) or {}
    l = Location(name=data.get('name', ''), region_id=data.get('region_id'), address=data.get('address', ''))
    db.session.add(l)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return fail('الموقع موجود بالفعل لهذه المنطقة', 400)
    return ok({'id': l.id}, 'تم إضافة الموقع')


@rest_api.route('/locations/<int:lid>', methods=['DELETE'])
@login_required
def api_location_delete(lid):
    l = Location.query.get_or_404(lid)
    db.session.delete(l)
    db.session.commit()
    return ok(message='تم حذف الموقع')


# ==================== WORK PLANS ====================

@rest_api.route('/work-plans')
@login_required
def api_work_plans_list():
    plan_type = request.args.get('plan_type', '')
    q = WorkPlan.query
    if plan_type:
        q = q.filter_by(plan_type=plan_type)
    plans = q.order_by(WorkPlan.plan_date.desc()).limit(200).all()
    return ok([p.to_dict() for p in plans])


@rest_api.route('/work-plans', methods=['POST'])
@login_required
def api_work_plan_create():
    data = request.get_json(force=True, silent=True) or {}
    p = WorkPlan(
        title=data.get('title', ''),
        description=data.get('description', ''),
        plan_type=data.get('plan_type', 'daily'),
        company_id=data.get('company_id'),
        region_id=data.get('region_id'),
        location_id=data.get('location_id'),
        plan_date=datetime.strptime(data['plan_date'], '%Y-%m-%d').date() if data.get('plan_date') else datetime.now().date(),
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data.get('due_date') else None,
        assigned_to=data.get('assigned_to'),
        created_by=current_user.id,
        status=data.get('status', 'pending'),
    )
    db.session.add(p)
    db.session.flush()

    tasks = data.get('tasks', [])
    for i, t in enumerate(tasks):
        task = WorkPlanTask(
            plan_id=p.id,
            title=t.get('title', ''),
            description=t.get('description', ''),
            order=i,
            assigned_to=t.get('assigned_to'),
            priority=t.get('priority', 'normal'),
            estimated_hours=t.get('estimated_hours'),
        )
        db.session.add(task)

    db.session.commit()
    return ok({'id': p.id}, 'تم إضافة خطة العمل')


@rest_api.route('/work-plans/<int:pid>', methods=['PUT'])
@login_required
def api_work_plan_update(pid):
    p = WorkPlan.query.get_or_404(pid)
    data = request.get_json(force=True, silent=True) or {}
    for field in ['title', 'description', 'plan_type', 'company_id', 'region_id', 'location_id', 'assigned_to', 'status', 'progress']:
        if field in data:
            setattr(p, field, data[field])
    if 'plan_date' in data and data['plan_date']:
        p.plan_date = datetime.strptime(data['plan_date'], '%Y-%m-%d').date()
    if 'due_date' in data and data['due_date']:
        p.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()

    if 'tasks' in data:
        existing_ids = {t.id for t in p.tasks}
        new_ids = set()
        for tdata in data['tasks']:
            tid = tdata.get('id')
            if tid and tid in existing_ids:
                task = WorkPlanTask.query.get(tid)
                if task:
                    task.title = tdata.get('title', task.title)
                    task.description = tdata.get('description', task.description)
                    task.assigned_to = tdata.get('assigned_to', task.assigned_to)
                    task.priority = tdata.get('priority', task.priority)
                    task.estimated_hours = tdata.get('estimated_hours', task.estimated_hours)
                    new_ids.add(tid)
            elif not tid and tdata.get('title'):
                task = WorkPlanTask(
                    plan_id=pid,
                    title=tdata['title'],
                    description=tdata.get('description', ''),
                    order=len(p.tasks),
                    assigned_to=tdata.get('assigned_to'),
                    priority=tdata.get('priority', 'normal'),
                    estimated_hours=tdata.get('estimated_hours'),
                )
                db.session.add(task)
        for oid in existing_ids - new_ids:
            ot = WorkPlanTask.query.get(oid)
            if ot:
                db.session.delete(ot)

    total = len(p.tasks) + sum(1 for t in data.get('tasks', []) if not t.get('id') and t.get('title'))
    completed = sum(1 for t in p.tasks if t.is_completed)
    p.progress = round(completed / total * 100) if total > 0 else 0
    if p.progress == 100:
        p.status = 'completed'

    db.session.commit()
    return ok(p.to_dict(), 'تم تحديث خطة العمل')


@rest_api.route('/work-plans/<int:pid>', methods=['DELETE'])
@login_required
def api_work_plan_delete(pid):
    p = WorkPlan.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return ok(message='تم حذف خطة العمل')


@rest_api.route('/work-plans/<int:pid>/tasks', methods=['POST'])
@login_required
def api_work_plan_task_add(pid):
    p = WorkPlan.query.get_or_404(pid)
    data = request.get_json(force=True, silent=True) or {}
    task = WorkPlanTask(
        plan_id=pid,
        title=data.get('title', ''),
        description=data.get('description', ''),
        order=data.get('order', len(p.tasks)),
        assigned_to=data.get('assigned_to'),
        priority=data.get('priority', 'normal'),
        estimated_hours=data.get('estimated_hours'),
    )
    db.session.add(task)
    db.session.commit()
    return ok({'id': task.id}, 'تم إضافة المهمة')


@rest_api.route('/work-plans/tasks/<int:tid>/complete', methods=['POST'])
@login_required
def api_work_plan_task_complete(tid):
    task = WorkPlanTask.query.get_or_404(tid)
    data = request.get_json(force=True, silent=True) or {}
    task.is_completed = True
    task.completed_at = datetime.utcnow()
    task.completed_by = data.get('completed_by')
    task.evaluation_score = data.get('evaluation_score')
    task.evaluation_notes = data.get('evaluation_notes', '')

    total = len(task.plan.tasks)
    completed = sum(1 for t in task.plan.tasks if t.is_completed or t.id == tid)
    task.plan.progress = round(completed / total * 100) if total > 0 else 0
    if task.plan.progress == 100:
        task.plan.status = 'completed'
    elif task.plan.progress > 0:
        task.plan.status = 'in_progress'

    db.session.commit()
    return ok(task.to_dict(), 'تم إتمام المهمة')


@rest_api.route('/work-plans/tasks/<int:tid>', methods=['DELETE'])
@login_required
def api_work_plan_task_delete(tid):
    task = WorkPlanTask.query.get_or_404(tid)
    db.session.delete(task)
    db.session.commit()
    return ok(message='تم حذف المهمة')


@rest_api.route('/work-plans/tasks/<int:tid>', methods=['PUT'])
@login_required
def api_work_plan_task_update(tid):
    task = WorkPlanTask.query.get_or_404(tid)
    data = request.get_json(force=True, silent=True) or {}
    for field in ['title', 'description', 'order', 'assigned_to', 'priority', 'estimated_hours']:
        if field in data:
            setattr(task, field, data[field])
    db.session.commit()
    return ok(task.to_dict(), 'تم تحديث المهمة')


# ==================== FINANCIAL ====================

@rest_api.route('/financial/dashboard')
@login_required
def api_financial_dashboard():
    total_income = db.session.query(func.sum(FinancialTransaction.amount)).filter_by(
        transaction_type='income').scalar() or 0
    total_expense = db.session.query(func.sum(FinancialTransaction.amount)).filter_by(
        transaction_type='expense').scalar() or 0
    return ok({
        'total_income': float(total_income),
        'total_expense': float(total_expense),
        'balance': float(total_income - total_expense),
    })


@rest_api.route('/financial/salaries')
@login_required
def api_salaries_list():
    q = Salary.query
    month = request.args.get('month_year')
    if month:
        parts = month.split('-')
        if len(parts) == 2 and len(parts[0]) == 4:
            month = f'{parts[1]}-{parts[0]}'
        q = q.filter_by(month_year=month)
    emp_id = request.args.get('employee_id')
    if emp_id:
        q = q.filter_by(employee_id=int(emp_id))
    salaries = q.order_by(Salary.id.desc()).limit(200).all()
    return ok([s.to_dict() for s in salaries])


def create_transaction_journal_entry(txn, data):
    """إنشاء قيد محاسبي للمعاملة المالية"""
    cash_account = Account.query.filter_by(code='110001').first()
    bank_account = Account.query.filter_by(code='110002').first()
    advances_account = Account.query.filter_by(code='130001').first()
    salary_payable = Account.query.filter_by(code='210001').first()
    cafeteria_expense = Account.query.filter_by(code='511009').first() or Account.query.filter_by(code='520001').first()
    restaurant_expense = Account.query.filter_by(code='511010').first() or Account.query.filter_by(code='520002').first()
    deduction_expense = Account.query.filter_by(code='510002').first()
    overtime_expense = Account.query.filter_by(code='510003').first()

    source_account = bank_account if txn.payment_method == 'bank' else cash_account
    emp = txn.employee
    emp_name = emp.name if emp else ''

    # تحديد حساب المورد المرتبط
    supplier_account = None
    if txn.supplier_id:
        from models import Supplier
        supplier = Supplier.query.get(txn.supplier_id)
        if supplier and supplier.payable_account_id:
            supplier_account = Account.query.get(supplier.payable_account_id)

    details = []

    if txn.transaction_type == 'advance':
        if source_account:
            details.append({'account_id': advances_account.id, 'debit': txn.amount, 'credit': 0, 'description': f'سلفة - {emp_name}'})
            details.append({'account_id': source_account.id, 'debit': 0, 'credit': txn.amount, 'description': f'صرف سلفة - {emp_name}'})
    elif txn.transaction_type == 'overtime':
        return None
    elif txn.transaction_type == 'deduction':
        return None
    elif txn.transaction_type == 'penalty':
        return None
    elif txn.transaction_type == 'cafeteria':
        return None
    elif txn.transaction_type == 'restaurant':
        return None

    if len(details) < 2:
        return None

    year = txn.date.year
    month = txn.date.month

    entry = JournalEntry(
        entry_number=f'TXN-{txn.date.strftime("%Y%m%d")}-{txn.id or 0}',
        date=txn.date,
        description=f'{txn.get_type_name()} - {emp_name}',
        reference_type='transaction',
        reference_id=txn.id,
        created_by=current_user.id,
    )
    db.session.add(entry)
    db.session.flush()

    for d in details:
        db.session.add(JournalEntryDetail(entry_id=entry.id, **d))

    return entry


def create_salary_journal_entry(salary, emp, month_year):
    """إنشاء قيد محاسبي متوازن للراتب
    القيد يسجل:
    1. مصروفات الدخل (أساسي + إقامة + إضافي) ← دائن مستحق الرواتب (total_earnings)
    2. تكاليف صاحب العمل (تأمينات + صحية + ملابس) ← أزواج متوازنة
    3. خصومات الموظف ← مدين مستحق الرواتب (خفض ما يحصل عليه)
    4. مطعم/بوفية بدون مورد ← مدين مصروف + دائن مستحق الرواتب
    """
    year, month = int(month_year.split('-')[1]), int(month_year.split('-')[0])

    salary_expense = Account.query.filter_by(code='511001').first() or Account.query.filter_by(code='510001').first()
    resident_expense = Account.query.filter_by(code='511002').first()
    overtime_expense = Account.query.filter_by(code='510003').first() or Account.query.filter_by(code='510002').first()
    insurance_expense = Account.query.filter_by(code='511003').first() or Account.query.filter_by(code='510003').first()
    clothing_expense = Account.query.filter_by(code='511004').first()
    health_expense = Account.query.filter_by(code='511005').first()
    deduction_expense = Account.query.filter_by(code='510002').first()
    cafeteria_expense = Account.query.filter_by(code='511009').first() or Account.query.filter_by(code='520001').first()
    restaurant_expense = Account.query.filter_by(code='511010').first() or Account.query.filter_by(code='520002').first()
    salary_payable = Account.query.filter_by(code='210001').first()
    insurance_payable = Account.query.filter_by(code='211003').first()
    health_payable = Account.query.filter_by(code='211004').first()
    clothing_payable = Account.query.filter_by(code='211005').first()

    details = []
    total_debit = 0
    total_credit = 0

    basic = float(salary.basic_salary_amount or 0)
    resident = float(salary.resident_allowance_amount or 0)
    overtime = float(salary.overtime_amount or 0)
    insurance = float(salary.insurance_amount or 0)
    health = float(salary.health_card_amount or 0)
    clothing = float(salary.clothing_allowance_amount or 0)
    advances = float(salary.advance_amount or 0)
    deductions = float(salary.deduction_amount or 0)
    penalties = float(salary.penalty_amount or 0)
    cafeteria = float(salary.cafeteria_deduction or 0)
    restaurant = float(salary.restaurant_deduction or 0)

    total_earnings = basic + resident + overtime

    if salary_expense and basic > 0:
        details.append({'account_id': salary_expense.id, 'debit': basic, 'credit': 0, 'description': f'راتب أساسي (بعد الخصومات) - {emp.name}'})
        total_debit += basic

    if resident_expense and resident > 0:
        details.append({'account_id': resident_expense.id, 'debit': resident, 'credit': 0, 'description': f'بدل إقامة - {emp.name}'})
        total_debit += resident

    if overtime_expense and overtime > 0:
        details.append({'account_id': overtime_expense.id, 'debit': overtime, 'credit': 0, 'description': f'عمل إضافي - {emp.name}'})
        total_debit += overtime

    if salary_payable and total_earnings > 0:
        details.append({'account_id': salary_payable.id, 'debit': 0, 'credit': total_earnings, 'description': f'إجمالي راتب - {emp.name}'})
        total_credit += total_earnings

    if advances > 0 and salary_payable:
        details.append({'account_id': salary_payable.id, 'debit': advances, 'credit': 0, 'description': f'خصم سلف - {emp.name}'})
        total_debit += advances

    if insurance_expense and insurance > 0:
        details.append({'account_id': insurance_expense.id, 'debit': insurance, 'credit': 0, 'description': f'تأمين - {emp.name}'})
        total_debit += insurance
    if insurance_payable and insurance > 0:
        details.append({'account_id': insurance_payable.id, 'debit': 0, 'credit': insurance, 'description': f'تأمينات مستحقة - {emp.name}'})
        total_credit += insurance

    if health_expense and health > 0:
        details.append({'account_id': health_expense.id, 'debit': health, 'credit': 0, 'description': f'بطاقة صحية - {emp.name}'})
        total_debit += health
    if health_payable and health > 0:
        details.append({'account_id': health_payable.id, 'debit': 0, 'credit': health, 'description': f'بطاقة صحية مستحقة - {emp.name}'})
        total_credit += health

    if clothing_expense and clothing > 0:
        details.append({'account_id': clothing_expense.id, 'debit': clothing, 'credit': 0, 'description': f'بدل ملابس - {emp.name}'})
        total_debit += clothing
    if clothing_payable and clothing > 0:
        details.append({'account_id': clothing_payable.id, 'debit': 0, 'credit': clothing, 'description': f'بدل ملابس مستحق - {emp.name}'})
        total_credit += clothing

    if len(details) < 2:
        return None

    if len(details) < 2:
        return None

    diff = total_debit - total_credit
    if abs(diff) > 0.01:
        if diff > 0:
            if salary_payable:
                details.append({'account_id': salary_payable.id, 'debit': 0, 'credit': round(diff, 2), 'description': f'فرق تصحيح - {emp.name}'})
                total_credit += round(diff, 2)
        else:
            if salary_payable:
                details.append({'account_id': salary_payable.id, 'debit': round(abs(diff), 2), 'credit': 0, 'description': f'فرق تصحيح - {emp.name}'})
                total_debit += round(abs(diff), 2)

    entry = JournalEntry(
        entry_number=f'SAL-{month_year}-{emp.code or emp.id}',
        date=datetime(year, month, min(28, 28)).date(),
        description=f'رواتب {emp.name} - {month_year}',
        reference_type='salary',
        reference_id=salary.id,
        created_by=current_user.id,
    )
    db.session.add(entry)
    db.session.flush()

    for d in details:
        db.session.add(JournalEntryDetail(entry_id=entry.id, **d))

    return entry


@rest_api.route('/financial/salary-calculation', methods=['POST'])
@login_required
def api_salary_calculation():
    data = request.get_json(force=True, silent=True) or {}
    month_year_input = data.get('month_year', datetime.now().strftime('%m-%Y'))
    company_id = data.get('company_id')
    create_entries = data.get('create_journal_entries', True)

    parts = month_year_input.split('-')
    if len(parts) == 2:
        if len(parts[0]) == 4:
            month_year = f'{parts[1]}-{parts[0]}'
            year, month = int(parts[0]), int(parts[1])
        else:
            month_year = month_year_input
            year, month = int(parts[1]), int(parts[0])
    else:
        month_year = datetime.now().strftime('%m-%Y')
        year, month = datetime.now().year, datetime.now().month

    # التحقق من الفترة المالية المفتوحة
    period_start = datetime(year, month, 1).date()
    period_end = datetime(year, month, 28).date() if month == 2 else datetime(year, month, 30).date()
    if month == 12:
        period_end = datetime(year, 12, 31).date()
    else:
        period_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

    period = FinancialPeriod.query.filter(
        FinancialPeriod.start_date <= period_start,
        FinancialPeriod.end_date >= period_end,
        FinancialPeriod.status == 'open'
    ).first()
    if not period:
        return fail(f'لا توجد فترة مالية مفتوحة لشهر {month_year}', 400)

    employees = Employee.query.filter_by(is_active=True)
    if company_id:
        employees = employees.filter_by(company_id=int(company_id))
    employees = employees.all()

    results = []
    created_entries = 0

    # قراءة إعدادات الخصومات التلقائية من النظام
    insurance_setting = SystemSettings.query.filter_by(setting_key='monthly_insurance', is_active=True).first()
    health_setting = SystemSettings.query.filter_by(setting_key='monthly_health', is_active=True).first()
    clothing_setting = SystemSettings.query.filter_by(setting_key='monthly_clothing', is_active=True).first()

    monthly_insurance = float(insurance_setting.value) if insurance_setting else 10800.0
    monthly_health = float(health_setting.value) if health_setting else 1250.0
    monthly_clothing = float(clothing_setting.value) if clothing_setting else 2040.0

    for emp in employees:
        existing = Salary.query.filter_by(employee_id=emp.id, month_year=month_year).first()
        if existing:
            results.append(existing.to_dict())
            continue

        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, days_in_month).date()

        attendances = Attendance.query.filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date,
        ).all()

        present_days = sum(1 for a in attendances if a.attendance_status in ['present', 'late'])
        sick_days = sum(1 for a in attendances if a.attendance_status == 'sick')
        annual_leave_days = sum(1 for a in attendances if a.attendance_status == 'annual_leave')

        daily_rate = emp.salary / 30
        basic_payout = round(daily_rate * present_days, 2)

        resident_allowance = 0
        if emp.is_resident:
            resident_allowance = round(500 * present_days, 2)

        transactions = FinancialTransaction.query.filter(
            FinancialTransaction.employee_id == emp.id,
            FinancialTransaction.is_settled == False,
        ).all()

        advances = sum(float(t.monthly_installment or t.amount) for t in transactions if t.transaction_type == 'advance' and not t.is_settled)
        overtime = sum(float(t.amount) for t in transactions if t.transaction_type == 'overtime')
        deductions = sum(float(t.amount) for t in transactions if t.transaction_type == 'deduction')
        penalties = sum(float(t.amount) for t in transactions if t.transaction_type == 'penalty')
        cafeteria = sum(float(t.amount) for t in transactions if t.transaction_type == 'cafeteria')
        restaurant = sum(float(t.amount) for t in transactions if t.transaction_type == 'restaurant')

        # تحديد موردي البوفية والمطعم من المعاملات
        cafeteria_supplier_id = None
        restaurant_supplier_id = None
        for t in transactions:
            if t.transaction_type == 'cafeteria' and t.supplier_id and not cafeteria_supplier_id:
                cafeteria_supplier_id = t.supplier_id
            if t.transaction_type == 'restaurant' and t.supplier_id and not restaurant_supplier_id:
                restaurant_supplier_id = t.supplier_id

        total_earnings = basic_payout + resident_allowance + overtime

        # تكاليف صاحب العمل (تأمينات، بطائق صحية، بدل ملابس) - لا تُخصم من راتب الموظف
        insurance_cost = monthly_insurance
        health_cost = monthly_health
        clothing_cost = monthly_clothing

        # الخصومات والجزاءات تُخصم من الراتب الأساسي فقط
        salary_deductions = deductions + penalties + cafeteria + restaurant
        basic_after_deductions = round(basic_payout - salary_deductions, 2)
        if basic_after_deductions < 0:
            basic_after_deductions = 0

        # صافي الراتب = (الراتب الأساسي بعد الخصومات) + بدل الإقامة + الإضافي - السلف
        total_earnings_after_deductions = basic_after_deductions + resident_allowance + overtime
        net_salary = round(total_earnings_after_deductions - advances, 2)

        salary = Salary(
            employee_id=emp.id,
            month_year=month_year,
            base_salary=emp.salary,
            attendance_days=present_days,
            basic_salary_amount=basic_after_deductions,
            resident_allowance_amount=resident_allowance,
            daily_allowance_amount=0,
            clothing_allowance_amount=clothing_cost,
            health_card_amount=health_cost,
            insurance_amount=insurance_cost,
            overtime_amount=overtime,
            advance_amount=advances,
            deduction_amount=deductions,
            penalty_amount=penalties,
            cafeteria_deduction=cafeteria,
            restaurant_deduction=restaurant,
            cafeteria_supplier_id=cafeteria_supplier_id,
            restaurant_supplier_id=restaurant_supplier_id,
            total_salary=net_salary,
            is_calculated=True,
            calculated_at=datetime.utcnow(),
        )
        db.session.add(salary)
        db.session.flush()

        if create_entries:
            if not check_duplicate_journal_entry('salary', salary.id):
                entry = create_salary_journal_entry(salary, emp, month_year)
                if entry:
                    salary.journal_entry_id = entry.id
                    created_entries += 1

        results.append(salary.to_dict())

    db.session.commit()
    return ok(results, f'تم حساب {len(results)} راتب - {created_entries} قيد محاسبي')


@rest_api.route('/financial/salaries/<int:sid>', methods=['DELETE'])
@login_required
def api_salary_delete(sid):
    s = Salary.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    return ok(message='تم حذف رواتب')


@rest_api.route('/financial/salaries/<int:sid>/pay', methods=['POST'])
@login_required
def api_salary_pay(sid):
    s = Salary.query.get_or_404(sid)
    data = request.get_json(force=True, silent=True) or {}
    payment_method = data.get('payment_method', 'cash')

    if payment_method == 'cash':
        account = Account.query.filter_by(code='110001').first()
    else:
        account = Account.query.filter_by(code='110002').first()

    amount = float(s.total_salary or 0)

    if account and float(account.get_balance() or 0) < amount:
        account_name = 'الصندوق' if payment_method == 'cash' else 'البنك'
        return fail(f'الرصيد غير كافٍ في {account_name} لصرف راتب {s.employee.name}. الرصيد الحالي: {account.get_balance()} ر.ي، المطلوب: {amount} ر.ي', 400)

    s.is_paid = True
    s.paid_date = datetime.now().date()
    s.payment_method = payment_method

    # إنشاء قيد الدفع
    salary_payable = Account.query.filter_by(code='210001').first()
    emp = s.employee
    emp_name = emp.name if emp else ''

    if account and salary_payable:
        entry = JournalEntry(
            entry_number=f'SALPAY-{s.id}-{datetime.now().strftime("%Y%m%d%H%M")}',
            date=datetime.now().date(),
            description=f'دفع راتب {emp_name} - {s.month_year}',
            reference_type='salary_pay',
            reference_id=s.id,
            created_by=current_user.id,
        )
        db.session.add(entry)
        db.session.flush()

        db.session.add(JournalEntryDetail(
            entry_id=entry.id,
            account_id=salary_payable.id,
            debit=amount,
            credit=0,
            description=f'خصم راتب مستحق - {emp_name}',
        ))
        db.session.add(JournalEntryDetail(
            entry_id=entry.id,
            account_id=account.id,
            debit=0,
            credit=amount,
            description=f'دفع راتب نقداً - {emp_name}' if payment_method == 'cash' else f'دفع راتب بنكي - {emp_name}',
        ))
        s.journal_entry_id = entry.id

    parts = s.month_year.split('-')
    if len(parts) == 2:
        if len(parts[0]) == 4:
            year, month = int(parts[0]), int(parts[1])
        else:
            year, month = int(parts[1]), int(parts[0])
        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, days_in_month).date()

        txns = FinancialTransaction.query.filter(
            FinancialTransaction.employee_id == s.employee_id,
            FinancialTransaction.is_settled == False,
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date,
        ).all()
        for t in txns:
            t.is_settled = True

    db.session.commit()
    return ok(s.to_dict(), 'تم تسجيل الدفع')


@rest_api.route('/financial/advances/settle', methods=['POST'])
@login_required
def api_advance_settle():
    """سداد سلفة (كاملة أو جزئية)"""
    data = request.get_json(force=True, silent=True) or {}
    employee_id = data.get('employee_id')
    amount = float(data.get('amount', 0))
    payment_method = data.get('payment_method', 'cash')

    if not employee_id or amount <= 0:
        return fail('يرجى تحديد الموظف والمبلغ', 400)

    # التحقق من الرصيد
    account_code = '110001' if payment_method == 'cash' else '110002'
    account = Account.query.filter_by(code=account_code).first()
    if account:
        current_balance = float(account.get_balance() or 0)
        if current_balance < amount:
            account_name = 'الصندوق' if payment_method == 'cash' else 'البنك'
            return fail(f'الرصيد غير كافٍ في {account_name}. الرصيد الحالي: {current_balance} ر.ي', 400)

    # البحث عن السلف غير المدفوعة
    unsettled_advances = FinancialTransaction.query.filter(
        FinancialTransaction.employee_id == employee_id,
        FinancialTransaction.transaction_type == 'advance',
        FinancialTransaction.is_settled == False,
    ).order_by(FinancialTransaction.date).all()

    if not unsettled_advances:
        return fail('لا توجد سلف مستحقة لهذا الموظف', 400)

    remaining = amount
    settled_count = 0
    for adv in unsettled_advances:
        if remaining <= 0:
            break
        adv_balance = float(adv.amount or 0)
        already_settled = float(adv.settled_amount or 0)
        remaining_balance = adv_balance - already_settled
        settle_amount = min(remaining, remaining_balance)
        adv.settled_amount = already_settled + settle_amount
        if adv.settled_amount >= adv_balance:
            adv.is_settled = True
            adv.settled_date = datetime.now().date()
            settled_count += 1
        remaining -= settle_amount

    # إنشاء معاملة سداد
    t = FinancialTransaction(
        employee_id=employee_id,
        date=datetime.now().date(),
        description=f'سداد سلفة - {amount:,.0f} ر.ي',
        amount=amount,
        transaction_type='advance_settlement',
        payment_method=payment_method,
        is_settled=True,
    )
    db.session.add(t)
    db.session.flush()

    # القيد المحاسبي: مدين مستحق الرواتب + دائن الصندوق/البنك
    salary_payable = Account.query.filter_by(code='210001').first()
    if account and salary_payable:
        entry = JournalEntry(
            entry_number=f'ADVSET-{t.id}-{datetime.now().strftime("%Y%m%d%H%M")}',
            date=datetime.now().date(),
            description=f'سداد سلفة - {amount:,.0f} ر.ي',
            reference_type='advance_settlement',
            reference_id=t.id,
            created_by=current_user.id,
        )
        db.session.add(entry)
        db.session.flush()
        db.session.add(JournalEntryDetail(
            entry_id=entry.id, account_id=salary_payable.id,
            debit=amount, credit=0,
            description=f'سداد سلفة',
        ))
        db.session.add(JournalEntryDetail(
            entry_id=entry.id, account_id=account.id,
            debit=0, credit=amount,
            description=f'سداد سلفة نقداً' if payment_method == 'cash' else f'سداد سلفة بنكياً',
        ))
        t.journal_entry_id = entry.id

    db.session.commit()
    return ok(t.to_dict(), f'تم سداد المبلغ {amount:,.0f} ر.ي من السلف')


@rest_api.route('/financial/advances/unsettled')
@login_required
def api_advances_unsettled():
    """السلف غير المدفوعة"""
    employee_id = request.args.get('employee_id')
    q = FinancialTransaction.query.filter(
        FinancialTransaction.transaction_type == 'advance',
        FinancialTransaction.is_settled == False,
    )
    if employee_id:
        q = q.filter_by(employee_id=int(employee_id))
    advances = q.order_by(FinancialTransaction.date).all()

    # تجميع حسب الموظف
    by_employee = {}
    for adv in advances:
        emp_id = adv.employee_id
        if emp_id not in by_employee:
            by_employee[emp_id] = {
                'employee_id': emp_id,
                'employee_name': adv.employee.name if adv.employee else '',
                'total_amount': 0,
                'monthly_installment': 0,
                'transactions': []
            }
        remaining = (adv.amount or 0) - (adv.settled_amount or 0)
        by_employee[emp_id]['total_amount'] += remaining
        by_employee[emp_id]['monthly_installment'] += float(adv.monthly_installment or 0)
        by_employee[emp_id]['transactions'].append({
            'id': adv.id,
            'amount': float(adv.amount or 0),
            'settled_amount': float(adv.settled_amount or 0),
            'remaining': remaining,
            'monthly_installment': float(adv.monthly_installment or 0),
            'date': adv.date.isoformat() if adv.date else '',
            'description': adv.description,
        })

    return ok(list(by_employee.values()))


@rest_api.route('/financial/transactions')
@login_required
def api_transactions_list():
    q = FinancialTransaction.query
    tx_type = request.args.get('type')
    if tx_type:
        q = q.filter_by(transaction_type=tx_type)
    emp_id = request.args.get('employee_id')
    if emp_id:
        q = q.filter_by(employee_id=int(emp_id))
    transactions = q.order_by(FinancialTransaction.date.desc()).limit(200).all()
    return ok([t.to_dict() for t in transactions])


@rest_api.route('/financial/transactions', methods=['POST'])
@login_required
def api_transaction_create():
    data = request.get_json(force=True, silent=True) or {}
    amount = float(data.get('amount', 0))
    payment_method = data.get('payment_method', 'cash')
    tx_type = data.get('transaction_type', 'advance')
    tx_date = datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else datetime.now().date()

    # التحقق من الفترة المالية المفتوحة
    period = FinancialPeriod.query.filter(
        FinancialPeriod.start_date <= tx_date,
        FinancialPeriod.end_date >= tx_date,
        FinancialPeriod.status == 'open'
    ).first()
    if not period:
        return fail('لا توجد فترة مالية مفتوحة لهذا التاريخ', 400)

    if tx_type in ['advance']:
        account_code = '110001' if payment_method == 'cash' else '110002'
        account = Account.query.filter_by(code=account_code).first()
        if account:
            current_balance = float(account.get_balance() or 0)
            if current_balance < amount:
                account_name = 'الصندوق' if payment_method == 'cash' else 'البنك'
                return fail(f'الرصيد غير كافٍ في {account_name}. الرصيد الحالي: {current_balance} ر.ي', 400)

    t = FinancialTransaction(
        employee_id=data.get('employee_id'),
        date=tx_date,
        description=data.get('description', ''),
        amount=amount,
        transaction_type=tx_type,
        payment_method=payment_method,
        supplier_id=data.get('supplier_id'),
        monthly_installment=float(data.get('monthly_installment', 0)),
    )
    db.session.add(t)
    db.session.flush()

    entry = create_transaction_journal_entry(t, data)
    if entry:
        t.journal_entry_id = entry.id

    db.session.commit()
    return ok(t.to_dict(), 'تم إضافة المعاملة')


# ==================== ACCOUNTS ====================

@rest_api.route('/accounts/balance')
@login_required
def api_accounts_balance():
    cash = Account.query.filter_by(code='110001').first()
    bank = Account.query.filter_by(code='110002').first()
    return ok({
        'cash': float(cash.get_balance()) if cash else 0,
        'bank': float(bank.get_balance()) if bank else 0,
        'total': float((cash.get_balance()) + (bank.get_balance())) if cash and bank else 0,
    })

@rest_api.route('/accounts')
@login_required
def api_accounts_list():
    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    return ok([a.to_dict() for a in accounts])


@rest_api.route('/accounts/chart')
@login_required
def api_accounts_chart():
    accounts = Account.query.order_by(Account.code).all()
    return ok([a.to_dict() for a in accounts])


@rest_api.route('/accounts', methods=['POST'])
@login_required
def api_account_create():
    data = request.get_json(force=True, silent=True) or {}
    a = Account(
        code=data.get('code', ''),
        name=data.get('name', ''),
        name_ar=data.get('name_ar', ''),
        account_type=data.get('account_type', ''),
        nature=data.get('nature', 'debit'),
        parent_id=data.get('parent_id'),
    )
    db.session.add(a)
    db.session.commit()
    return ok({'id': a.id}, 'تم إضافة الحساب')


@rest_api.route('/accounts/<int:aid>', methods=['PUT'])
@login_required
def api_account_update(aid):
    a = Account.query.get_or_404(aid)
    data = request.get_json(force=True, silent=True) or {}
    for field in ['code', 'name_ar', 'name_en', 'account_type', 'parent_id', 'is_active']:
        if field in data:
            setattr(a, field, data[field])
    db.session.commit()
    return ok(message='تم تحديث الحساب')


@rest_api.route('/accounts/<int:aid>', methods=['DELETE'])
@login_required
def api_account_delete(aid):
    a = Account.query.get_or_404(aid)
    # فحص الارتباط بسجلات أخرى
    has_journal_entries = JournalEntryDetail.query.filter_by(account_id=aid).first()
    if has_journal_entries:
        return fail('لا يمكن حذف الحساب لأنه مرتبط بقيود يومية', 400)
    has_children = Account.query.filter_by(parent_id=aid).first()
    if has_children:
        return fail('لا يمكن حذف الحساب لأنه يحتوي على حسابات فرعية', 400)
    db.session.delete(a)
    db.session.commit()
    return ok(message='تم حذف الحساب')


@rest_api.route('/accounts/journal')
@login_required
def api_journal_list():
    entries = JournalEntry.query.order_by(JournalEntry.date.desc()).limit(200).all()
    return ok([e.to_dict() for e in entries])


@rest_api.route('/accounts/journal', methods=['POST'])
@login_required
def api_journal_add():
    data = request.get_json(force=True, silent=True) or {}
    details = data.get('details', [])
    total_debit = sum(d.get('debit', 0) for d in details)
    total_credit = sum(d.get('credit', 0) for d in details)
    if abs(total_debit - total_credit) > 0.01:
        return fail('المدين لا يساوي الدائن - القيد غير متوازن', 400)

    entry = JournalEntry(
        entry_number=data.get('entry_number', f'JE-{datetime.now().strftime("%Y%m%d%H%M")}'),
        date=datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else datetime.now().date(),
        description=data.get('description', ''),
        created_by=current_user.id,
    )
    db.session.add(entry)
    db.session.flush()
    for detail in details:
        d = JournalEntryDetail(
            entry_id=entry.id,
            account_id=detail.get('account_id'),
            debit=detail.get('debit', 0),
            credit=detail.get('credit', 0),
            description=detail.get('description', ''),
        )
        db.session.add(d)
    db.session.commit()
    return ok({'id': entry.id}, 'تم إضافة القيد')


@rest_api.route('/accounts/journal/<int:jid>', methods=['DELETE'])
@login_required
def api_journal_delete(jid):
    entry = JournalEntry.query.get_or_404(jid)
    JournalEntryDetail.query.filter_by(entry_id=jid).delete()
    db.session.delete(entry)
    db.session.commit()
    return ok(message='تم حذف القيد')


@rest_api.route('/accounts/journal/bulk-reverse', methods=['POST'])
@login_required
def api_journal_bulk_reverse():
    """عكس قيود خاطئة بالجملة"""
    data = request.get_json(force=True, silent=True) or {}
    entry_ids = data.get('entry_ids', [])
    if not entry_ids:
        return fail('معرفات القيود مطلوبة', 400)

    reversed_count = 0
    errors = []
    for eid in entry_ids:
        entry = JournalEntry.query.get(eid)
        if not entry:
            errors.append(f'القيد {eid} غير موجود')
            continue
        existing_reverse = JournalEntry.query.filter(
            JournalEntry.reference_type == 'reverse',
            JournalEntry.reference_id == entry.id
        ).first()
        if existing_reverse:
            errors.append(f'القيد {entry.entry_number} تم عكسه مسبقاً')
            continue

        reverse_entry = JournalEntry(
            entry_number=f'REV-{entry.entry_number}',
            date=datetime.now().date(),
            description=f'عكس قيد خاطئ: {entry.entry_number} - {entry.description}',
            reference_type='reverse',
            reference_id=entry.id,
            created_by=current_user.id,
        )
        db.session.add(reverse_entry)
        db.session.flush()

        for detail in entry.details:
            db.session.add(JournalEntryDetail(
                entry_id=reverse_entry.id,
                account_id=detail.account_id,
                debit=detail.credit,
                credit=detail.debit,
                description=f'عكس: {detail.description}',
            ))
        reversed_count += 1

    db.session.commit()
    return ok({'reversed': reversed_count, 'errors': errors}, f'تم عكس {reversed_count} قيود')


@rest_api.route('/accounts/trial-balance')
@login_required
def api_trial_balance():
    accounts = Account.query.filter_by(is_active=True).order_by(Account.code).all()
    result = []
    total_debit = 0
    total_credit = 0
    for a in accounts:
        balance = float(a.get_balance())
        if a.nature == 'debit':
            if balance >= 0:
                d, c = balance, 0
            else:
                d, c = 0, abs(balance)
        else:
            if balance >= 0:
                d, c = 0, balance
            else:
                d, c = abs(balance), 0
        if d > 0 or c > 0:
            result.append({'code': a.code, 'name': a.name_ar or a.name, 'debit': d, 'credit': c, 'nature': a.nature})
            total_debit += d
            total_credit += c
    return ok({'accounts': result, 'total_debit': round(total_debit, 2), 'total_credit': round(total_credit, 2)})


@rest_api.route('/accounts/income-statement')
@login_required
def api_income_statement():
    revenue_accounts = Account.query.filter_by(account_type='revenue', is_active=True).all()
    expense_accounts = Account.query.filter_by(account_type='expense', is_active=True).all()
    total_revenue = sum(abs(float(a.get_balance())) for a in revenue_accounts)
    total_expense = sum(abs(float(a.get_balance())) for a in expense_accounts)
    return ok({
        'revenue': [{'code': a.code, 'name': a.name_ar or a.name, 'balance': abs(float(a.get_balance()))} for a in revenue_accounts],
        'expense': [{'code': a.code, 'name': a.name_ar or a.name, 'balance': abs(float(a.get_balance()))} for a in expense_accounts],
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'net_income': total_revenue - total_expense,
    })


@rest_api.route('/accounts/balance-sheet')
@login_required
def api_balance_sheet():
    asset_accounts = Account.query.filter_by(account_type='asset', is_active=True).all()
    liability_accounts = Account.query.filter_by(account_type='liability', is_active=True).all()
    equity_accounts = Account.query.filter_by(account_type='equity', is_active=True).all()
    revenue_accounts = Account.query.filter_by(account_type='revenue', is_active=True).all()
    expense_accounts = Account.query.filter_by(account_type='expense', is_active=True).all()
    
    total_assets = sum(float(a.get_balance()) for a in asset_accounts)
    total_liabilities = sum(float(a.get_balance()) for a in liability_accounts)
    total_equity = sum(float(a.get_balance()) for a in equity_accounts)
    total_revenue = sum(float(a.get_balance()) for a in revenue_accounts)
    total_expense = sum(float(a.get_balance()) for a in expense_accounts)
    net_income = total_revenue - total_expense
    
    return ok({
        'assets': [{'code': a.code, 'name': a.name_ar or a.name, 'balance': float(a.get_balance())} for a in asset_accounts],
        'liabilities': [{'code': a.code, 'name': a.name_ar or a.name, 'balance': float(a.get_balance())} for a in liability_accounts],
        'equity': [{'code': a.code, 'name': a.name_ar or a.name, 'balance': float(a.get_balance())} for a in equity_accounts],
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'net_income': net_income,
    })


@rest_api.route('/accounts/statement')
@login_required
def api_account_statement():
    """كشف حساب لحساب معين في فترة محددة"""
    try:
        account_id = request.args.get('account_id')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        search = request.args.get('search', '').strip()

        if account_id:
            account = Account.query.get(int(account_id))
            if not account:
                return fail('الحساب غير موجود', 404)

            details = JournalEntryDetail.query.filter_by(account_id=account.id).all()
            if date_from:
                df = datetime.strptime(date_from, '%Y-%m-%d').date()
                details = [d for d in details if d.entry and d.entry.date and d.entry.date >= df]
            if date_to:
                dt = datetime.strptime(date_to, '%Y-%m-%d').date()
                details = [d for d in details if d.entry and d.entry.date and d.entry.date <= dt]

            details.sort(key=lambda d: d.entry.date if d.entry and d.entry.date else datetime.min.date())

            transactions = []
            running_balance = 0
            for d in details:
                entry = d.entry
                running_balance += float(d.debit or 0) - float(d.credit or 0)
                transactions.append({
                    'date': entry.date.strftime('%Y-%m-%d') if entry.date else '',
                    'entry_number': entry.entry_number or '',
                    'description': d.description or entry.description or '',
                    'debit': float(d.debit or 0),
                    'credit': float(d.credit or 0),
                    'balance': running_balance,
                })

            return ok({
                'account': {'id': account.id, 'code': account.code, 'name': account.name_ar or account.name, 'type': account.account_type},
                'transactions': transactions,
                'total_debit': sum(t['debit'] for t in transactions),
                'total_credit': sum(t['credit'] for t in transactions),
                'final_balance': running_balance,
            })
        else:
            q = Account.query.filter_by(is_active=True)
            if search:
                q = q.filter((Account.code.contains(search)) | (Account.name.contains(search)) | (Account.name_ar.contains(search)))
            accounts = q.order_by(Account.code).all()
            return ok([{
                'id': a.id, 'code': a.code, 'name': a.name_ar or a.name,
                'type': a.account_type, 'balance': float(a.get_balance() or 0),
            } for a in accounts])
    except Exception as e:
        return fail(str(e), 500)


# ==================== SUPPLIERS ====================

@rest_api.route('/suppliers')
@login_required
def api_suppliers_list():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return ok([s.to_dict() for s in suppliers])


@rest_api.route('/suppliers', methods=['POST'])
@login_required
def api_supplier_create():
    data = request.get_json(force=True, silent=True) or {}
    s = Supplier(
        name=data.get('name', ''),
        name_ar=data.get('name_ar', data.get('name', '')),
        contact_person=data.get('contact_person', ''),
        phone=data.get('phone', ''),
        email=data.get('email', ''),
        address=data.get('address', data.get('location', '')),
        supplier_type=data.get('supplier_type', 'general'),
    )
    db.session.add(s)
    db.session.flush()
    s.get_or_create_payable_account()
    db.session.commit()
    return ok(s.to_dict(), 'تم إضافة المورد')


@rest_api.route('/suppliers/<int:sid>', methods=['PUT'])
@login_required
def api_supplier_update(sid):
    s = Supplier.query.get_or_404(sid)
    data = request.get_json(force=True, silent=True) or {}
    for field in ['name', 'name_ar', 'contact_person', 'phone', 'email', 'address']:
        if field in data:
            setattr(s, field, data[field])
    db.session.commit()
    return ok(message='تم تحديث المورد')


@rest_api.route('/suppliers/<int:sid>', methods=['DELETE'])
@login_required
def api_supplier_delete(sid):
    s = Supplier.query.get_or_404(sid)
    # فحص الارتباط بسجلات أخرى
    has_invoices = SupplierInvoice.query.filter_by(supplier_id=sid).first()
    if has_invoices:
        return fail('لا يمكن حذف المورد لأنه مرتبط بفواتير موردين', 400)
    has_transactions = FinancialTransaction.query.filter_by(supplier_id=sid).first()
    if has_transactions:
        return fail('لا يمكن حذف المورد لأنه مرتبط بمعاملات مالية', 400)
    has_salaries_cafeteria = Salary.query.filter_by(cafeteria_supplier_id=sid).first()
    if has_salaries_cafeteria:
        return fail('لا يمكن حذف المورد لأنه مرتبط برواتب (بوفية)', 400)
    has_salaries_restaurant = Salary.query.filter_by(restaurant_supplier_id=sid).first()
    if has_salaries_restaurant:
        return fail('لا يمكن حذف المورد لأنه مرتبط برواتب (مطعم)', 400)
    db.session.delete(s)
    db.session.commit()
    return ok(message='تم حذف المورد')


@rest_api.route('/supplier-invoices')
@login_required
def api_supplier_invoices():
    q = SupplierInvoice.query
    supplier_id = request.args.get('supplier_id')
    if supplier_id:
        q = q.filter_by(supplier_id=int(supplier_id))
    invoices = q.order_by(SupplierInvoice.id.desc()).limit(200).all()

    result = [{
        'id': f'inv_{inv.id}',
        'source': 'invoice',
        'supplier_id': inv.supplier_id,
        'supplier_name': inv.supplier.name if inv.supplier else '',
        'invoice_number': inv.invoice_number or '',
        'amount': float(inv.amount) if inv.amount else 0,
        'paid_amount': float(inv.paid_amount) if inv.paid_amount else 0,
        'remaining_amount': float(inv.remaining_amount) if inv.remaining_amount else 0,
        'date': inv.invoice_date.strftime('%Y-%m-%d') if inv.invoice_date else '',
        'is_paid': inv.status == 'paid' if inv.status else False,
        'status': inv.status or 'pending',
    } for inv in invoices]

    cafeteria_supplier = Supplier.query.filter_by(supplier_type='cafeteria').first()
    restaurant_supplier = Supplier.query.filter_by(supplier_type='restaurant').first()

    show_cafeteria = not supplier_id or (cafeteria_supplier and int(supplier_id) == cafeteria_supplier.id)
    show_restaurant = not supplier_id or (restaurant_supplier and int(supplier_id) == restaurant_supplier.id)

    if show_cafeteria and cafeteria_supplier:
        caf_salaries = Salary.query.filter(Salary.cafeteria_deduction > 0).all()
        unpaid_caf = [s for s in caf_salaries if not s.cafeteria_paid_to_supplier]
        total_caf = sum(float(s.cafeteria_deduction or 0) for s in unpaid_caf)
        total_caf_all = sum(float(s.cafeteria_deduction or 0) for s in caf_salaries)
        if total_caf_all > 0:
            month = caf_salaries[0].month_year if caf_salaries else ''
            all_paid = all(s.cafeteria_paid_to_supplier for s in caf_salaries)
            result.append({
                'id': 'sal_group_cafeteria',
                'source': 'salary_deduction_group',
                'deduction_type': 'cafeteria',
                'supplier_id': cafeteria_supplier.id,
                'supplier_name': cafeteria_supplier.name or '',
                'invoice_number': f'بوفية - مخصصات الرواتب - {month}',
                'amount': total_caf_all,
                'paid_amount': total_caf_all - total_caf,
                'remaining_amount': total_caf,
                'date': '',
                'is_paid': all_paid,
                'status': 'paid' if all_paid else ('partial' if (total_caf_all - total_caf) > 0 else 'pending'),
                'salary_ids': [s.id for s in unpaid_caf],
                'employee_count': len(unpaid_caf),
                'employee_count_total': len(caf_salaries),
            })

    if show_restaurant and restaurant_supplier:
        rest_salaries = Salary.query.filter(Salary.restaurant_deduction > 0).all()
        unpaid_rest = [s for s in rest_salaries if not s.restaurant_paid_to_supplier]
        total_rest = sum(float(s.restaurant_deduction or 0) for s in unpaid_rest)
        total_rest_all = sum(float(s.restaurant_deduction or 0) for s in rest_salaries)
        if total_rest_all > 0:
            month = rest_salaries[0].month_year if rest_salaries else ''
            all_paid = all(s.restaurant_paid_to_supplier for s in rest_salaries)
            result.append({
                'id': 'sal_group_restaurant',
                'source': 'salary_deduction_group',
                'deduction_type': 'restaurant',
                'supplier_id': restaurant_supplier.id,
                'supplier_name': restaurant_supplier.name or '',
                'invoice_number': f'مطعم - مخصصات الرواتب - {month}',
                'amount': total_rest_all,
                'paid_amount': total_rest_all - total_rest,
                'remaining_amount': total_rest,
                'date': '',
                'is_paid': all_paid,
                'status': 'paid' if all_paid else ('partial' if (total_rest_all - total_rest) > 0 else 'pending'),
                'salary_ids': [s.id for s in unpaid_rest],
                'employee_count': len(unpaid_rest),
                'employee_count_total': len(rest_salaries),
            })

    result.sort(key=lambda x: x.get('date', ''), reverse=True)
    return ok(result)


@rest_api.route('/supplier-invoices/<int:iid>/delete', methods=['POST'])
@login_required
def api_supplier_invoice_delete(iid):
    """حذف فاتورة مورد"""
    try:
        inv = SupplierInvoice.query.get_or_404(iid)
        if inv.paid_amount and inv.paid_amount > 0:
            return fail('لا يمكن حذف فاتورة تم دفع جزء منها', 400)
        db.session.delete(inv)
        db.session.commit()
        return ok(None, 'تم حذف الفاتورة')
    except Exception as e:
        db.session.rollback()
        return fail(str(e), 500)


@rest_api.route('/salary-deduction/pay', methods=['POST'])
@login_required
def api_salary_deduction_pay():
    """دفع مخصصات مورد (بوفية/مطعم) من الرواتب - فردي أو جماعي"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        salary_ids = data.get('salary_ids', [])
        deduction_type = data.get('deduction_type', 'cafeteria')
        payment_method = data.get('payment_method', 'cash')

        if not salary_ids:
            return fail('معرفات الرواتب مطلوبة', 400)

        salaries = Salary.query.filter(Salary.id.in_(salary_ids)).all()
        if not salaries:
            return fail('لا توجد رواتب', 400)

        if deduction_type == 'cafeteria':
            supplier = Supplier.query.filter_by(supplier_type='cafeteria').first()
        else:
            supplier = Supplier.query.filter_by(supplier_type='restaurant').first()

        if not supplier:
            return fail('المورد غير موجود', 400)

        total_amount = 0
        for sal in salaries:
            if deduction_type == 'cafeteria':
                total_amount += float(sal.cafeteria_deduction or 0)
            else:
                total_amount += float(sal.restaurant_deduction or 0)

        if total_amount <= 0:
            return fail('لا يوجد مبلغ مخصص', 400)

        if payment_method == 'cash':
            cash_account = Account.query.filter_by(code='110001').first()
        else:
            cash_account = Account.query.filter_by(code='110002').first()

        if cash_account and float(cash_account.get_balance() or 0) < total_amount:
            account_name = 'الصندوق' if payment_method == 'cash' else 'البنك'
            return fail(f'الرصيد غير كافٍ في {account_name}. الرصيد الحالي: {cash_account.get_balance()} ر.ي', 400)

        supplier_account = None
        if supplier.payable_account_id:
            supplier_account = Account.query.get(supplier.payable_account_id)

        if not supplier_account:
            return fail('حساب المورد غير موجود', 400)

        type_name = 'بوفية' if deduction_type == 'cafeteria' else 'مطعم'
        month = salaries[0].month_year if salaries else ''

        if cash_account and supplier_account:
            entry = JournalEntry(
                entry_number=f'SALPAY-{deduction_type[:3].upper()}-{datetime.now().strftime("%Y%m%d%H%M")}',
                date=datetime.now().date(),
                description=f'دفع مخصصات {type_name} - {month} - {len(salaries)} موظف',
                reference_type='salary_deduction_pay',
                reference_id=salaries[0].id,
                created_by=current_user.id,
            )
            db.session.add(entry)
            db.session.flush()

            db.session.add(JournalEntryDetail(
                entry_id=entry.id, account_id=supplier_account.id,
                debit=0, credit=total_amount,
                description=f'خصم {type_name} - {month}',
            ))
            db.session.add(JournalEntryDetail(
                entry_id=entry.id, account_id=cash_account.id,
                debit=total_amount, credit=0,
                description=f'دفع {type_name} - {month}',
            ))

        for sal in salaries:
            if deduction_type == 'cafeteria':
                sal.cafeteria_paid_to_supplier = True
            else:
                sal.restaurant_paid_to_supplier = True

        db.session.commit()
        return ok({'amount': total_amount, 'type': deduction_type, 'count': len(salaries)}, f'تم دفع {total_amount} ر.ي')
    except Exception as e:
        db.session.rollback()
        return fail(str(e), 500)


@rest_api.route('/salary-deduction/voucher', methods=['POST'])
@login_required
def api_salary_deduction_voucher():
    """بيانات سند صرف لمخصصات المورد (جماعي)"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        salary_ids = data.get('salary_ids', [])
        deduction_type = data.get('deduction_type', 'cafeteria')

        salaries = Salary.query.filter(Salary.id.in_(salary_ids)).all()
        type_name = 'بوفية' if deduction_type == 'cafeteria' else 'مطعم'

        if deduction_type == 'cafeteria':
            supplier = Supplier.query.filter_by(supplier_type='cafeteria').first()
        else:
            supplier = Supplier.query.filter_by(supplier_type='restaurant').first()

        details = []
        total = 0
        month = ''
        for sal in salaries:
            emp = sal.employee
            amt = float(sal.cafeteria_deduction or 0) if deduction_type == 'cafeteria' else float(sal.restaurant_deduction or 0)
            total += amt
            month = sal.month_year
            details.append({
                'employee_name': emp.name if emp else '',
                'employee_code': emp.code if emp else '',
                'month_year': sal.month_year,
                'amount': amt,
            })

        return ok({
            'type': type_name,
            'total': total,
            'employee_count': len(details),
            'month_year': month,
            'supplier_name': supplier.name if supplier else '',
            'details': details,
        })
    except Exception as e:
        return fail(str(e), 500)


# ==================== PAYMENTS & RECEIPTS ====================

@rest_api.route('/supplier-invoices/<int:iid>/pay', methods=['POST'])
@login_required
def api_supplier_invoice_pay(iid):
    """دفع فاتورة مورد"""
    try:
        inv = SupplierInvoice.query.get_or_404(iid)
        data = request.get_json(force=True, silent=True) or {}
        amount = float(data.get('amount', 0))
        payment_method = data.get('payment_method', 'cash')

        if amount <= 0:
            return fail('المبلغ يجب أن يكون أكبر من صفر', 400)
        if amount > float(inv.remaining_amount or 0):
            return fail(f'المبلغ المدفوع ({amount}) أكبر من المتبقي ({inv.remaining_amount})', 400)

        if payment_method == 'cash':
            cash_account = Account.query.filter_by(code='110001').first()
        else:
            cash_account = Account.query.filter_by(code='110002').first()

        if cash_account and float(cash_account.get_balance() or 0) < amount:
            account_name = 'الصندوق' if payment_method == 'cash' else 'البنك'
            return fail(f'الرصيد غير كافٍ في {account_name}. الرصيد الحالي: {cash_account.get_balance()} ر.ي', 400)

        supplier = inv.supplier
        supplier_account = None
        if supplier and supplier.payable_account_id:
            supplier_account = Account.query.get(supplier.payable_account_id)

        inv.paid_amount = float(inv.paid_amount or 0) + amount
        inv.remaining_amount = float(inv.amount or 0) - inv.paid_amount
        if inv.remaining_amount <= 0:
            inv.status = 'paid'
        else:
            inv.status = 'partial'
        inv.payment_method = payment_method

        payment = SupplierInvoicePayment(
            invoice_id=inv.id,
            amount=amount,
            payment_date=datetime.now().date(),
            payment_method=payment_method,
            created_by=current_user.id,
        )
        db.session.add(payment)

        if supplier_account and cash_account:
            if not check_duplicate_journal_entry('supplier_invoice_pay', inv.id):
                entry = JournalEntry(
                    entry_number=f'SUPPAY-{inv.id}-{datetime.now().strftime("%Y%m%d%H%M")}',
                    date=datetime.now().date(),
                    description=f'دفع فاتورة مورد {supplier.name} - فاتورة #{inv.invoice_number}',
                    reference_type='supplier_invoice_pay',
                    reference_id=inv.id,
                    created_by=current_user.id,
                )
                db.session.add(entry)
                db.session.flush()

                db.session.add(JournalEntryDetail(
                    entry_id=entry.id, account_id=supplier_account.id,
                    debit=amount, credit=0,
                    description=f'دفع فاتورة #{inv.invoice_number} - {supplier.name}',
                ))
                db.session.add(JournalEntryDetail(
                    entry_id=entry.id, account_id=cash_account.id,
                    debit=0, credit=amount,
                    description=f'دفع فاتورة مورد {supplier.name}' if payment_method == 'cash' else f'تحويل بنكي لمورد {supplier.name}',
                ))

        db.session.commit()
        return ok(inv.to_dict(), f'تم دفع {amount} ر.ي')
    except Exception as e:
        db.session.rollback()
        return fail(str(e), 500)


@rest_api.route('/supplier-invoices/<int:iid>/voucher')
@login_required
def api_supplier_invoice_voucher(iid):
    """بيانات سند دفع فاتورة مورد للطباعة"""
    inv = SupplierInvoice.query.get_or_404(iid)
    supplier = inv.supplier
    payments = SupplierInvoicePayment.query.filter_by(invoice_id=iid).order_by(SupplierInvoicePayment.payment_date).all()
    
    return ok({
        'invoice': {
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'amount': float(inv.amount or 0),
            'paid_amount': float(inv.paid_amount or 0),
            'remaining_amount': float(inv.remaining_amount or 0),
            'status': inv.status,
            'invoice_date': str(inv.invoice_date) if inv.invoice_date else '',
        },
        'supplier': {
            'id': supplier.id if supplier else 0,
            'name': supplier.name if supplier else '',
            'name_ar': supplier.name_ar if supplier else '',
            'phone': supplier.phone if supplier else '',
        },
        'payments': [{
            'id': p.id,
            'amount': float(p.amount or 0),
            'payment_date': str(p.payment_date) if p.payment_date else '',
            'payment_method': p.payment_method or 'cash',
        } for p in payments],
        'company_name': 'طلعت هائل للخدمات والاستشارات الزراعية',
    })


@rest_api.route('/invoices/<int:iid>/receive', methods=['POST'])
@login_required
def api_invoice_receive(iid):
    """استلام مبلغ من عميل (شركة) مقابل فاتورة"""
    try:
        inv = Invoice.query.get_or_404(iid)
        data = request.get_json(force=True, silent=True) or {}
        amount = float(data.get('amount', 0))
        payment_method = data.get('payment_method', 'cash')

        if amount <= 0:
            return fail('المبلغ يجب أن يكون أكبر من صفر', 400)
        remaining = float(inv.amount or 0) - float(inv.paid_amount or 0)
        if amount > remaining:
            return fail(f'المبلغ ({amount}) أكبر من المتبقي ({remaining})', 400)

        if payment_method == 'cash':
            cash_account = Account.query.filter_by(code='110001').first()
        else:
            cash_account = Account.query.filter_by(code='110002').first()

        company_account = None
        contract = inv.contract
        company_name = ''
        if contract and contract.company:
            company = contract.company
            company_name = company.name or ''
            if company.receivable_account_id:
                company_account = Account.query.get(company.receivable_account_id)

        inv.paid_amount = float(inv.paid_amount or 0) + amount
        if inv.paid_amount >= float(inv.amount or 0):
            inv.is_paid = True
            inv.paid_date = datetime.now().date()
        inv.payment_method = payment_method

        if cash_account and company_account:
            if not check_duplicate_journal_entry('invoice_receive', inv.id):
                entry = JournalEntry(
                    entry_number=f'COMREC-{inv.id}-{datetime.now().strftime("%Y%m%d%H%M")}',
                    date=datetime.now().date(),
                    description=f'استلام مبلغ من {company_name} - فاتورة #{inv.invoice_number}',
                    reference_type='invoice_receive',
                    reference_id=inv.id,
                    created_by=current_user.id,
                )
                db.session.add(entry)
                db.session.flush()

                db.session.add(JournalEntryDetail(
                    entry_id=entry.id, account_id=cash_account.id,
                    debit=amount, credit=0,
                    description=f'استلام من {company_name} - فاتورة #{inv.invoice_number}',
                ))
                db.session.add(JournalEntryDetail(
                    entry_id=entry.id, account_id=company_account.id,
                    debit=0, credit=amount,
                    description=f'خصم فاتورة #{inv.invoice_number} - {company_name}',
                ))

        db.session.commit()
        return ok(inv.to_dict(), f'تم استلام {amount} ر.ي')
    except Exception as e:
        db.session.rollback()
        return fail(str(e), 500)


@rest_api.route('/financial/salaries/<int:sid>/voucher')
@login_required
def api_salary_voucher(sid):
    """بيانات سند صرف راتب للطباعة"""
    s = Salary.query.get_or_404(sid)
    emp = s.employee
    company = emp.company if emp else None
    return ok({
        'salary_id': s.id,
        'employee_name': emp.name if emp else '',
        'employee_code': emp.code if emp else '',
        'company_name': company.name if company else '',
        'month_year': s.month_year,
        'total_salary': float(s.total_salary) if s.total_salary else 0,
        'basic_salary_amount': float(s.basic_salary_amount) if s.basic_salary_amount else 0,
        'resident_allowance_amount': float(s.resident_allowance_amount) if s.resident_allowance_amount else 0,
        'overtime_amount': float(s.overtime_amount) if s.overtime_amount else 0,
        'advance_amount': float(s.advance_amount) if s.advance_amount else 0,
        'deduction_amount': float(s.deduction_amount) if s.deduction_amount else 0,
        'penalty_amount': float(s.penalty_amount) if s.penalty_amount else 0,
        'cafeteria_deduction': float(s.cafeteria_deduction) if s.cafeteria_deduction else 0,
        'restaurant_deduction': float(s.restaurant_deduction) if s.restaurant_deduction else 0,
        'cafeteria_supplier_name': s.cafeteria_supplier.name if s.cafeteria_supplier else '',
        'restaurant_supplier_name': s.restaurant_supplier.name if s.restaurant_supplier else '',
        'payment_method': s.payment_method or 'cash',
        'payment_method_name': 'بنكي' if s.payment_method == 'bank' else 'نقداً',
        'paid_date': s.paid_date.strftime('%Y-%m-%d') if s.paid_date else '',
        'is_paid': s.is_paid,
    })


# ==================== REPORTS ====================

@rest_api.route('/reports/dashboard')
@login_required
def api_reports_dashboard():
    total_employees = Employee.query.filter_by(is_active=True).count()
    today = datetime.now().date()
    today_attendance = Attendance.query.filter_by(date=today, attendance_status='present').count()
    pending_transactions = FinancialTransaction.query.filter_by(is_settled=False).count()
    pending_salaries = Salary.query.filter_by(is_paid=False).count()
    return ok({
        'total_employees': total_employees,
        'today_attendance': today_attendance,
        'pending_transactions': pending_transactions,
        'pending_salaries': pending_salaries,
    })


@rest_api.route('/reports/attendance')
@login_required
def api_reports_attendance():
    today = datetime.now().date()
    from datetime import timedelta

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    company_id = request.args.get('company_id')

    if date_from:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
    else:
        start_date = today - timedelta(days=30)

    if date_to:
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        end_date = today

    q = Attendance.query.filter(Attendance.date >= start_date, Attendance.date <= end_date)

    if company_id:
        emp_ids = [e.id for e in Employee.query.filter_by(company_id=int(company_id)).all()]
        q = q.filter(Attendance.employee_id.in_(emp_ids))

    daily_counts = db.session.query(
        Attendance.date,
        Attendance.attendance_status,
        func.count(Attendance.id)
    ).filter(Attendance.date >= start_date, Attendance.date <= end_date)
    if company_id:
        daily_counts = daily_counts.filter(Attendance.employee_id.in_(emp_ids))
    daily_counts = daily_counts.group_by(Attendance.date, Attendance.attendance_status).all()

    daily_map = {}
    for date_val, status, count in daily_counts:
        ds = date_val.strftime('%m/%d')
        if ds not in daily_map:
            daily_map[ds] = {'date': ds, 'date_full': date_val.strftime('%Y-%m-%d'), 'present': 0, 'late': 0, 'absent': 0, 'sick': 0, 'annual_leave': 0}
        daily_map[ds][status] = count

    total_by_status = db.session.query(
        Attendance.attendance_status, func.count(Attendance.id)
    ).filter(Attendance.date >= start_date, Attendance.date <= end_date)
    if company_id:
        total_by_status = total_by_status.filter(Attendance.employee_id.in_(emp_ids))
    total_by_status = total_by_status.group_by(Attendance.attendance_status).all()

    total_days = sum(c for _, c in total_by_status)
    present_total = sum(c for s, c in total_by_status if s in ('present', 'late'))

    # Group attendance by company
    companies = Company.query.all()
    company_map = {c.id: c.name for c in companies}
    emp_company = {}
    for emp in Employee.query.all():
        emp_company[emp.id] = emp.company_id

    company_daily = {}
    for att in q.all():
        cid = emp_company.get(att.employee_id)
        cname = company_map.get(cid, 'بدون شركة')
        if cname not in company_daily:
            company_daily[cname] = {}
        ds = att.date.strftime('%m/%d')
        if ds not in company_daily[cname]:
            company_daily[cname][ds] = {'date': ds, 'date_full': att.date.strftime('%Y-%m-%d'), 'present': 0, 'late': 0, 'absent': 0, 'sick': 0, 'annual_leave': 0}
        company_daily[cname][ds][att.attendance_status] = company_daily[cname][ds].get(att.attendance_status, 0) + 1

    companies_result = []
    for cname, daily in company_daily.items():
        days = sorted(daily.values(), key=lambda x: x['date'])
        td = sum(sum(v for k, v in d.items() if k not in ('date', 'date_full')) for d in days)
        pt = sum(d.get('present', 0) + d.get('late', 0) for d in days)
        companies_result.append({
            'company_name': cname,
            'daily': days,
            'total_days': td,
            'attendance_rate': round(pt / td * 100, 1) if td > 0 else 0,
        })

    return ok({
        'daily': sorted(daily_map.values(), key=lambda x: x['date']),
        'summary': {s: c for s, c in total_by_status},
        'period': f'{start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")}',
        'total_days': total_days,
        'attendance_rate': round(present_total / total_days * 100, 1) if total_days > 0 else 0,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'companies': companies_result,
    })


@rest_api.route('/reports/financial')
@login_required
def api_reports_financial():
    from datetime import timedelta
    from calendar import monthrange
    today = datetime.now().date()
    month_year = request.args.get('month_year')

    if month_year:
        parts = month_year.split('-')
        if len(parts) == 2:
            if len(parts[0]) == 4:
                y, m = int(parts[0]), int(parts[1])
            else:
                y, m = int(parts[1]), int(parts[0])
        else:
            y, m = today.year, today.month
        start_date = datetime(y, m, 1).date()
        days_in_month = monthrange(y, m)[1]
        end_date = datetime(y, m, days_in_month).date()
    else:
        start_date = today.replace(day=1)
        end_date = today

    total_by_type = db.session.query(
        FinancialTransaction.transaction_type,
        func.sum(FinancialTransaction.amount),
        func.count(FinancialTransaction.id)
    ).filter(FinancialTransaction.date >= start_date, FinancialTransaction.date <= end_date
    ).group_by(FinancialTransaction.transaction_type).all()

    monthly_data = {}
    for i in range(11, -1, -1):
        month_date = today - timedelta(days=30 * i)
        key = month_date.strftime('%m/%Y')
        monthly_data[key] = {'month': key, 'income': 0, 'expense': 0, 'count': 0}

    all_tx = FinancialTransaction.query.filter(
        FinancialTransaction.date >= today - timedelta(days=365)
    ).all()
    for t in all_tx:
        key = t.date.strftime('%m/%Y') if t.date else None
        if key and key in monthly_data:
            if t.transaction_type in ('overtime',):
                monthly_data[key]['income'] += float(t.amount or 0)
            else:
                monthly_data[key]['expense'] += float(t.amount or 0)
            monthly_data[key]['count'] += 1

    total_income = sum(float(s or 0) for t, s, c in total_by_type if t in ('overtime',))
    total_expense = sum(float(s or 0) for t, s, c in total_by_type if t in ('advance', 'deduction', 'penalty', 'cafeteria', 'restaurant'))

    # Group by company
    company_map = {c.id: c.name for c in Company.query.all()}
    emp_company = {e.id: e.company_id for e in Employee.query.all()}
    company_transactions = FinancialTransaction.query.filter(
        FinancialTransaction.date >= start_date, FinancialTransaction.date <= end_date
    ).all()
    companies_data = {}
    for t in company_transactions:
        cid = emp_company.get(t.employee_id)
        cname = company_map.get(cid, 'بدون شركة') if cid else 'بدون شركة'
        if cname not in companies_data:
            companies_data[cname] = {'income': 0, 'expense': 0, 'count': 0, 'by_type': {}}
        ct = companies_data[cname]
        ct['count'] += 1
        tp = t.transaction_type or 'other'
        ct['by_type'][tp] = ct['by_type'].get(tp, 0) + float(t.amount or 0)
        if tp in ('overtime',):
            ct['income'] += float(t.amount or 0)
        else:
            ct['expense'] += float(t.amount or 0)

    return ok({
        'by_type': [{'type': t, 'total': float(s or 0), 'count': c} for t, s, c in total_by_type],
        'monthly': list(monthly_data.values()),
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'month_year': month_year or 'current',
        'period': f'{start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")}',
        'companies': [{'company_name': k, **v} for k, v in companies_data.items()],
    })


@rest_api.route('/reports/employees')
@login_required
def api_reports_employees():
    company_id = request.args.get('company_id')
    q = Employee.query.filter_by(is_active=True)
    if company_id:
        q = q.filter_by(company_id=int(company_id))
    employees = q.all()
    companies = Company.query.all()
    company_map = {c.id: c.name for c in companies}

    by_company = {}
    total_salary = 0
    for e in employees:
        cname = company_map.get(e.company_id, 'غير محدد')
        by_company[cname] = by_company.get(cname, 0) + 1
        total_salary += float(e.total_salary or e.salary or 0)

    return ok({
        'employees': [{
            'id': e.id,
            'name': e.name,
            'job_title': e.job_title or '',
            'company_id': e.company_id,
            'company_name': company_map.get(e.company_id, ''),
            'salary': float(e.salary) if e.salary else 0,
            'total_salary': float(e.total_salary or e.salary or 0),
            'is_active': e.is_active,
        } for e in employees],
        'by_company': [{'name': k, 'count': v} for k, v in by_company.items()],
        'total': len(employees),
        'total_salary': float(sum(e.salary or 0 for e in employees)),
        'companies': [
            {
                'company_name': cname,
                'employees': [
                    {
                        'id': e.id, 'name': e.name, 'job_title': e.job_title or '',
                        'salary': float(e.salary) if e.salary else 0,
                        'total_salary': float(e.total_salary or e.salary or 0),
                        'is_active': e.is_active,
                    } for e in employees if company_map.get(e.company_id) == cname
                ],
                'count': cnt,
                'total_salary': sum(float(e.total_salary or e.salary or 0) for e in employees if company_map.get(e.company_id) == cname),
            }
            for cname, cnt in by_company.items()
        ],
    })


@rest_api.route('/reports/evaluations')
@login_required
def api_reports_evaluations():
    month_year = request.args.get('month_year')

    q = Evaluation.query
    if month_year:
        parts = month_year.split('-')
        if len(parts) == 2:
            if len(parts[0]) == 4:
                y, m = int(parts[0]), int(parts[1])
            else:
                y, m = int(parts[1]), int(parts[0])
            from calendar import monthrange
            start_date = datetime(y, m, 1).date()
            end_date = datetime(y, m, monthrange(y, m)[1]).date()
            q = q.filter(Evaluation.date >= start_date, Evaluation.date <= end_date)

    evaluations = q.order_by(Evaluation.date.desc()).all()
    employees = Employee.query.filter_by(is_active=True).all()
    companies = Company.query.all()

    total_evals = len(evaluations)
    avg_score = sum(e.score for e in evaluations) / total_evals if total_evals > 0 else 0

    rating_dist = {'ممتاز': 0, 'جيد جداً': 0, 'جيد': 0, 'مقبول': 0, 'ضعيف': 0}
    for e in evaluations:
        r = e.get_rating()
        if r in rating_dist:
            rating_dist[r] += 1

    emp_scores = {}
    for e in evaluations:
        if e.employee_id not in emp_scores:
            emp_scores[e.employee_id] = {'scores': [], 'name': e.employee.name if e.employee else '', 'job': e.employee.job_title if e.employee else ''}
        emp_scores[e.employee_id]['scores'].append(e.score)

    emp_avg = []
    for eid, data in emp_scores.items():
        scores = data['scores']
        emp_avg.append({
            'employee_id': eid,
            'name': data['name'],
            'job_title': data['job'],
            'avg_score': round(sum(scores) / len(scores), 1),
            'eval_count': len(scores),
            'rating': 'ممتاز' if sum(scores)/len(scores) >= 9 else 'جيد جداً' if sum(scores)/len(scores) >= 7 else 'جيد' if sum(scores)/len(scores) >= 5 else 'مقبول' if sum(scores)/len(scores) >= 3 else 'ضعيف',
        })
    emp_avg.sort(key=lambda x: x['avg_score'], reverse=True)

    type_dist = {}
    for e in evaluations:
        t = e.get_type_name()
        type_dist[t] = type_dist.get(t, 0) + 1

    monthly_trend = {}
    for e in evaluations:
        key = e.date.strftime('%Y-%m') if e.date else 'غير محدد'
        if key not in monthly_trend:
            monthly_trend[key] = {'total': 0, 'sum': 0}
        monthly_trend[key]['total'] += 1
        monthly_trend[key]['sum'] += e.score

    trend_data = [{'month': k, 'count': v['total'], 'avg': round(v['sum']/v['total'], 1)} for k, v in sorted(monthly_trend.items(), reverse=True)[:6]]

    # Group by company
    company_map = {c.id: c.name for c in companies}
    emp_company = {e.id: e.company_id for e in employees}
    company_evals = {}
    for e in evaluations:
        cid = emp_company.get(e.employee_id)
        cname = company_map.get(cid, 'بدون شركة')
        if cname not in company_evals:
            company_evals[cname] = {'evaluations': [], 'scores': [], 'count': 0}
        company_evals[cname]['evaluations'].append(e)
        company_evals[cname]['scores'].append(e.score)
        company_evals[cname]['count'] += 1

    companies_result = []
    for cname, cd in company_evals.items():
        avg = round(sum(cd['scores']) / len(cd['scores']), 1) if cd['scores'] else 0
        companies_result.append({
            'company_name': cname,
            'total_evaluations': cd['count'],
            'avg_score': avg,
            'avg_rating': 'ممتاز' if avg >= 9 else 'جيد جداً' if avg >= 7 else 'جيد' if avg >= 5 else 'مقبول' if avg >= 3 else 'ضعيف',
        })

    return ok({
        'total_evaluations': total_evals,
        'avg_score': round(avg_score, 1),
        'avg_rating': 'ممتاز' if avg_score >= 9 else 'جيد جداً' if avg_score >= 7 else 'جيد' if avg_score >= 5 else 'مقبول' if avg_score >= 3 else 'ضعيف',
        'rating_distribution': [{'name': k, 'value': v} for k, v in rating_dist.items()],
        'type_distribution': [{'name': k, 'value': v} for k, v in type_dist.items()],
        'top_employees': emp_avg[:10],
        'bottom_employees': emp_avg[-5:] if len(emp_avg) >= 5 else emp_avg,
        'monthly_trend': trend_data,
        'all_employees': emp_avg,
        'month_year': month_year or 'all',
        'companies': companies_result,
    })


# ==================== DASHBOARD ====================

@rest_api.route('/dashboard/stats')
@login_required
def api_dashboard_stats():
    today = datetime.now().date()
    result = {}

    def safe_count(query_func, default=0):
        try:
            return query_func() or default
        except Exception:
            db.session.rollback()
            return default

    def safe_sum(query_func, default=0):
        try:
            return query_func() or default
        except Exception:
            db.session.rollback()
            return default

    result['total_employees'] = safe_count(lambda: Employee.query.filter_by(is_active=True).count())
    result['today_attendance'] = safe_count(lambda: Attendance.query.filter_by(date=today, attendance_status='present').count())
    result['late_count'] = safe_count(lambda: Attendance.query.filter_by(date=today, attendance_status='late').count())
    result['absent_count'] = safe_count(lambda: Attendance.query.filter_by(date=today, attendance_status='absent').count())
    result['sick_count'] = safe_count(lambda: Attendance.query.filter_by(date=today, attendance_status='sick').count())
    result['leave_count'] = safe_count(lambda: Attendance.query.filter_by(date=today, attendance_status='annual_leave').count())
    result['pending_transactions'] = safe_count(lambda: FinancialTransaction.query.filter_by(is_settled=False).count())
    result['pending_salaries'] = safe_count(lambda: Salary.query.filter_by(is_paid=False).count())

    result['total_income'] = safe_sum(lambda: db.session.query(func.sum(FinancialTransaction.amount)).filter_by(transaction_type='income').scalar())
    result['total_expense'] = safe_sum(lambda: db.session.query(func.sum(FinancialTransaction.amount)).filter_by(transaction_type='expense').scalar())

    result['total_salaries_paid'] = safe_sum(lambda: db.session.query(func.sum(Salary.total_salary)).filter_by(is_paid=True).scalar())
    result['total_salaries_unpaid'] = safe_sum(lambda: db.session.query(func.sum(Salary.total_salary)).filter_by(is_paid=False).scalar())

    result['work_plans_total'] = safe_count(lambda: WorkPlan.query.count())
    result['work_plans_completed'] = safe_count(lambda: WorkPlan.query.filter_by(status='completed').count())
    result['work_plans_in_progress'] = safe_count(lambda: WorkPlan.query.filter_by(status='in_progress').count())
    result['work_plans_pending'] = safe_count(lambda: WorkPlan.query.filter_by(status='pending').count())
    result['work_plan_tasks_total'] = safe_count(lambda: WorkPlanTask.query.count())
    result['work_plan_tasks_completed'] = safe_count(lambda: WorkPlanTask.query.filter_by(is_completed=True).count())

    result['total_companies'] = safe_count(lambda: Company.query.count())
    result['total_suppliers'] = safe_count(lambda: Supplier.query.count())
    result['active_contracts'] = safe_count(lambda: Contract.query.filter_by(status='active').count() if hasattr(Contract, 'query') else 0)

    result['recent_attendance'] = []
    try:
        recent_attendance = Attendance.query.filter_by(date=today).order_by(Attendance.id.desc()).limit(10).all()
        result['recent_attendance'] = [{
            'employee_name': r.employee.name if r.employee else '',
            'status': r.attendance_status,
            'time': r.check_in_time.strftime('%H:%M') if r.check_in_time else '',
        } for r in recent_attendance]
    except Exception:
        db.session.rollback()

    result['recent_transactions'] = []
    try:
        recent_transactions = FinancialTransaction.query.order_by(FinancialTransaction.date.desc()).limit(10).all()
        result['recent_transactions'] = [{
            'description': t.description or '',
            'amount': t.amount,
            'type': t.transaction_type,
            'date': t.date.strftime('%Y-%m-%d') if t.date else '',
        } for t in recent_transactions]
    except Exception:
        db.session.rollback()

    result['overdue_plans'] = safe_count(lambda: WorkPlan.query.filter(
        WorkPlan.status.in_(['pending', 'in_progress']),
        WorkPlan.due_date < today
    ).count())

    from sqlalchemy import func as sa_func
    result['top_employees'] = []
    try:
        top_employees = db.session.query(
            Employee.name,
            sa_func.avg(Evaluation.score).label('avg_score'),
            sa_func.count(Evaluation.id).label('eval_count')
        ).join(Evaluation, Evaluation.employee_id == Employee.id).group_by(
            Employee.id
        ).having(sa_func.count(Evaluation.id) > 0).order_by(
            sa_func.avg(Evaluation.score).desc()
        ).limit(5).all()
        result['top_employees'] = [{'name': t[0], 'score': round(float(t[1]), 1), 'count': t[2]} for t in top_employees]
    except Exception:
        db.session.rollback()

    result['recent_evaluations'] = []
    try:
        recent_evaluations = Evaluation.query.order_by(Evaluation.date.desc()).limit(5).all()
        result['recent_evaluations'] = [{
            'employee_name': e.employee.name if e.employee else '',
            'score': e.score,
            'date': e.date.strftime('%Y-%m-%d') if e.date else '',
        } for e in recent_evaluations]
    except Exception:
        db.session.rollback()

    return ok(result)


# ==================== SETTINGS ====================

@rest_api.route('/settings')
@login_required
def api_settings():
    allowances = AllowanceSetting.query.all()
    return ok({
        'company_name': 'طلعت هائل للخدمات والاستشارات الزراعية',
        'allowances': [{'id': a.id, 'name': a.name, 'amount': float(a.amount)} for a in allowances] if allowances else [],
    })


@rest_api.route('/settings', methods=['PUT'])
@login_required
def api_settings_update():
    data = request.get_json(force=True, silent=True) or {}
    return ok(message='تم حفظ الإعدادات')


@rest_api.route('/settings/change-password', methods=['POST'])
@login_required
def api_change_password():
    from werkzeug.security import generate_password_hash, check_password_hash
    data = request.get_json(force=True, silent=True) or {}
    current = data.get('current_password', '')
    new_pass = data.get('new_password', '')
    if not current or not new_pass:
        return fail('جميع الحقول مطلوبة')
    user = User.query.get(current_user.id)
    if not check_password_hash(user.password, current):
        return fail('كلمة المرور الحالية غير صحيحة')
    user.password = generate_password_hash(new_pass)
    db.session.commit()
    return ok(message='تم تحديث كلمة المرور بنجاح')


# ==================== USERS (admin) ====================

@rest_api.route('/users')
@login_required
def api_users_list():
    users = User.query.all()
    return ok([u.to_dict() for u in users])


@rest_api.route('/users', methods=['POST'])
@login_required
def api_user_create():
    from werkzeug.security import generate_password_hash
    import json
    data = request.get_json(force=True, silent=True) or {}
    if User.query.filter_by(username=data.get('username')).first():
        return fail('اسم المستخدم موجود مسبقاً')
    u = User(
        username=data.get('username', ''),
        password=generate_password_hash(data.get('password', '')),
        full_name=data.get('full_name', ''),
        role=data.get('role', 'viewer'),
        employee_id=data.get('employee_id'),
        company_id=data.get('company_id'),
        allowed_pages=json.dumps(data.get('allowed_pages', [])),
    )
    db.session.add(u)
    db.session.commit()
    return ok(u.to_dict(), 'تم إضافة المستخدم')


@rest_api.route('/users/<int:uid>', methods=['PUT'])
@login_required
def api_user_update(uid):
    from werkzeug.security import generate_password_hash
    import json
    u = User.query.get_or_404(uid)
    data = request.get_json(force=True, silent=True) or {}
    if 'full_name' in data:
        u.full_name = data['full_name']
    if 'role' in data:
        u.role = data['role']
    if 'password' in data and data['password']:
        u.password = generate_password_hash(data['password'])
    if 'employee_id' in data:
        u.employee_id = data.get('employee_id')
    if 'company_id' in data:
        u.company_id = data.get('company_id')
    if 'allowed_pages' in data:
        u.allowed_pages = json.dumps(data.get('allowed_pages', []))
    db.session.commit()
    return ok(u.to_dict(), 'تم تحديث المستخدم')


@rest_api.route('/users/<int:uid>', methods=['DELETE'])
@login_required
def api_user_delete(uid):
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        return fail('لا يمكن حذف المستخدم الحالي')
    db.session.delete(u)
    db.session.commit()
    return ok(message='تم حذف المستخدم')


# ==================== CONTRACTS ====================

@rest_api.route('/contracts')
@login_required
def api_contracts_list():
    contracts = Contract.query.order_by(Contract.id.desc()).all()
    return ok([{
        'id': c.id,
        'contract_type': c.contract_type or '',
        'company_id': c.company_id,
        'company_name': c.company.name if c.company else '',
        'contract_value': float(c.contract_value) if c.contract_value else 0,
        'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else '',
        'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else '',
        'amount_received': float(c.amount_received) if c.amount_received else 0,
        'remaining_amount': float(c.remaining_amount) if c.remaining_amount else 0,
        'status': c.status or 'active',
        'notes': c.notes or '',
    } for c in contracts])


@rest_api.route('/contracts', methods=['POST'])
@login_required
def api_contract_create():
    data = request.get_json(force=True, silent=True) or {}
    c = Contract(
        company_id=data.get('company_id'),
        contract_type=data.get('contract_type', 'monthly'),
        contract_value=data.get('contract_value', data.get('total_amount', 0)),
        notes=data.get('notes', data.get('description', '')),
    )
    if data.get('start_date'):
        c.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    if data.get('end_date'):
        c.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    db.session.add(c)
    db.session.commit()
    return ok({'id': c.id}, 'تم إضافة العقد')


@rest_api.route('/contracts/<int:cid>', methods=['PUT'])
@login_required
def api_contract_update(cid):
    c = Contract.query.get_or_404(cid)
    data = request.get_json(force=True, silent=True) or {}
    for field in ['company_id', 'contract_type', 'notes', 'status']:
        if field in data:
            setattr(c, field, data[field])
    if 'contract_value' in data or 'total_amount' in data:
        c.contract_value = data.get('contract_value', data.get('total_amount', c.contract_value))
    if 'start_date' in data and data['start_date']:
        c.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    if 'end_date' in data and data['end_date']:
        c.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    db.session.commit()
    return ok(message='تم تحديث العقد')


@rest_api.route('/contracts/<int:cid>', methods=['DELETE'])
@login_required
def api_contract_delete(cid):
    c = Contract.query.get_or_404(cid)
    # فحص الارتباط بسجلات أخرى
    has_invoices = Invoice.query.filter_by(contract_id=cid).first()
    if has_invoices:
        return fail('لا يمكن حذف العقد لأنه مرتبط بفواتير', 400)
    db.session.delete(c)
    db.session.commit()
    return ok(message='تم حذف العقد')


# ==================== INVOICES ====================

@rest_api.route('/invoices')
@login_required
def api_invoices_list():
    invoices = Invoice.query.order_by(Invoice.id.desc()).all()
    return ok([{
        'id': i.id,
        'invoice_number': i.invoice_number or '',
        'contract_id': i.contract_id,
        'company_name': i.contract.company.name if i.contract and i.contract.company else '',
        'amount': float(i.amount) if i.amount else 0,
        'paid_amount': float(i.paid_amount) if i.paid_amount else 0,
        'date': i.invoice_date.strftime('%Y-%m-%d') if i.invoice_date else '',
        'due_date': i.due_date.strftime('%Y-%m-%d') if i.due_date else '',
        'is_paid': i.is_paid,
    } for i in invoices])


@rest_api.route('/invoices', methods=['POST'])
@login_required
def api_invoice_create():
    data = request.get_json(force=True, silent=True) or {}
    i = Invoice(
        invoice_number=data.get('invoice_number', ''),
        contract_id=data.get('contract_id'),
        amount=data.get('amount', 0),
        invoice_date=datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else datetime.now().date(),
    )
    if data.get('due_date'):
        i.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
    db.session.add(i)
    db.session.flush()

    # إنشاء قيد محاسبي: مدين = ذمم مدينة الشركة، دائن = إيرادات
    if i.contract and i.contract.company:
        company = i.contract.company
        if company.receivable_account_id:
            company_account = Account.query.get(company.receivable_account_id)
            revenue_account = Account.query.filter_by(code='410004').first()
            if company_account and revenue_account:
                entry = JournalEntry(
                    entry_number=f'INV-{i.id}-{datetime.now().strftime("%Y%m%d%H%M")}',
                    date=i.invoice_date or datetime.now().date(),
                    description=f'إنشاء فاتورة #{i.invoice_number} - {company.name}',
                    reference_type='invoice',
                    reference_id=i.id,
                    created_by=current_user.id,
                )
                db.session.add(entry)
                db.session.flush()
                db.session.add(JournalEntryDetail(
                    entry_id=entry.id, account_id=company_account.id,
                    debit=float(i.amount or 0), credit=0,
                    description=f'فاتورة #{i.invoice_number} - {company.name}',
                ))
                db.session.add(JournalEntryDetail(
                    entry_id=entry.id, account_id=revenue_account.id,
                    debit=0, credit=float(i.amount or 0),
                    description=f'إيراد فاتورة #{i.invoice_number} - {company.name}',
                ))
    db.session.commit()
    return ok({'id': i.id}, 'تم إضافة الفاتورة')


# ==================== EXPENSE CATEGORIES ====================

@rest_api.route('/expense-categories')
@login_required
def api_expense_categories():
    cats = ExpenseCategory.query.all()
    return ok([{
        'id': c.id,
        'name': c.name or '',
        'name_ar': c.name_ar if hasattr(c, 'name_ar') else '',
        'account_code': c.account_code if hasattr(c, 'account_code') else '',
    } for c in cats])


# ==================== SUPPLIER INVOICES (extended) ====================

@rest_api.route('/supplier-invoices', methods=['POST'])
@login_required
def api_supplier_invoice_create():
    data = request.get_json(force=True, silent=True) or {}
    try:
        inv = SupplierInvoice(
            supplier_id=data.get('supplier_id'),
            invoice_number=data.get('invoice_number', ''),
            amount=data.get('amount', 0),
            paid_amount=0,
            remaining_amount=data.get('amount', 0),
            status='pending',
            created_by=current_user.id,
        )
        if data.get('date'):
            inv.invoice_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        else:
            inv.invoice_date = datetime.now().date()
        db.session.add(inv)
        db.session.flush()

        # إنشاء قيد محاسبي: مدين = مصروف، دائن = ذمم دائنة المورد
        supplier = None
        if inv.supplier_id:
            from models import Supplier
            supplier = Supplier.query.get(inv.supplier_id)
        if supplier and supplier.payable_account_id:
            supplier_account = Account.query.get(supplier.payable_account_id)
            # تحديد حساب المصروف حسب نوع المورد
            expense_account = None
            if supplier.supplier_type == 'cafeteria':
                expense_account = Account.query.filter_by(code='511009').first()
            elif supplier.supplier_type == 'restaurant':
                expense_account = Account.query.filter_by(code='511010').first()
            else:
                expense_account = Account.query.filter_by(code='520001').first()
            if supplier_account and expense_account:
                entry = JournalEntry(
                    entry_number=f'SUPINV-{inv.id}-{datetime.now().strftime("%Y%m%d%H%M")}',
                    date=inv.invoice_date or datetime.now().date(),
                    description=f'فاتورة مورد {supplier.name} - #{inv.invoice_number}',
                    reference_type='supplier_invoice',
                    reference_id=inv.id,
                    created_by=current_user.id,
                )
                db.session.add(entry)
                db.session.flush()
                db.session.add(JournalEntryDetail(
                    entry_id=entry.id, account_id=expense_account.id,
                    debit=float(inv.amount or 0), credit=0,
                    description=f'فاتورة مورد {supplier.name} - #{inv.invoice_number}',
                ))
                db.session.add(JournalEntryDetail(
                    entry_id=entry.id, account_id=supplier_account.id,
                    debit=0, credit=float(inv.amount or 0),
                    description=f'فاتورة مورد {supplier.name} - #{inv.invoice_number}',
                ))
        db.session.commit()
        return ok({'id': inv.id}, 'تم إضافة فاتورة المورد')
    except Exception as e:
        db.session.rollback()
        return fail(str(e), 500)


@rest_api.route('/reports/contractor-profit')
@login_required
def api_contractor_profit():
    """تقرير أرباح المتعهد - طلعت هائل"""
    data = request.args
    month_year = data.get('month_year', datetime.now().strftime('%m-%Y'))
    company_id = data.get('company_id')

    parts = month_year.split('-')
    if len(parts) == 2:
        if len(parts[0]) == 4:
            year, month = int(parts[0]), int(parts[1])
        else:
            year, month = int(parts[1]), int(parts[0])
    else:
        year, month = datetime.now().year, datetime.now().month

    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]

    insurance_setting = SystemSettings.query.filter_by(setting_key='monthly_insurance', is_active=True).first()
    health_setting = SystemSettings.query.filter_by(setting_key='monthly_health', is_active=True).first()
    clothing_setting = SystemSettings.query.filter_by(setting_key='monthly_clothing', is_active=True).first()
    monthly_insurance = float(insurance_setting.value) if insurance_setting else 10800.0
    monthly_health = float(health_setting.value) if health_setting else 1250.0
    monthly_clothing = float(clothing_setting.value) if clothing_setting else 2040.0

    employees = Employee.query.filter_by(is_active=True)
    if company_id:
        employees = employees.filter_by(company_id=int(company_id))
    employees = employees.all()

    results = []
    total_revenue = 0
    total_basic_paid = 0
    total_resident_paid = 0
    total_insurance_cost = 0
    total_health_cost = 0
    total_clothing_cost = 0
    total_profit = 0

    for emp in employees:
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, days_in_month).date()
        attendances = Attendance.query.filter(
            Attendance.employee_id == emp.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date,
        ).all()

        present_days = sum(1 for a in attendances if a.attendance_status in ['present', 'late'])
        absent_days = days_in_month - present_days

        base_salary = emp.basic_salary or emp.salary or 0
        revenue = emp.total_salary or base_salary

        basic_paid = round((base_salary / 30) * present_days, 2)
        resident_paid = round(500 * present_days, 2) if emp.is_resident else 0

        overtime_txns = FinancialTransaction.query.filter(
            FinancialTransaction.employee_id == emp.id,
            FinancialTransaction.transaction_type == 'overtime',
            FinancialTransaction.date >= start_date,
            FinancialTransaction.date <= end_date,
        ).all()
        overtime_amount = sum(t.amount for t in overtime_txns)

        total_employee_paid = basic_paid + resident_paid + overtime_amount

        insurance_cost = monthly_insurance
        health_cost = monthly_health
        clothing_cost = monthly_clothing
        total_employer_costs = insurance_cost + health_cost + clothing_cost

        profit = revenue - total_employee_paid - total_employer_costs

        results.append({
            'employee_id': emp.id,
            'employee_name': emp.name,
            'job_title': emp.job_title or '',
            'company_name': emp.company.name if emp.company else '',
            'is_resident': emp.is_resident,
            'base_salary': base_salary,
            'total_salary_revenue': revenue,
            'days_in_month': days_in_month,
            'present_days': present_days,
            'absent_days': absent_days,
            'basic_paid': basic_paid,
            'resident_paid': resident_paid,
            'overtime_amount': overtime_amount,
            'total_employee_paid': total_employee_paid,
            'insurance_cost': insurance_cost,
            'health_cost': health_cost,
            'clothing_cost': clothing_cost,
            'total_employer_costs': total_employer_costs,
            'profit': profit,
        })

        total_revenue += revenue
        total_basic_paid += basic_paid
        total_resident_paid += resident_paid
        total_insurance_cost += insurance_cost
        total_health_cost += health_cost
        total_clothing_cost += clothing_cost
        total_profit += profit

    # Group by company
    companies_map = {}
    for r in results:
        cname = r['company_name'] or 'بدون شركة'
        if cname not in companies_map:
            companies_map[cname] = {
                'company_name': cname,
                'employees': [],
                'total_revenue': 0, 'total_basic_paid': 0, 'total_resident_paid': 0,
                'total_overtime': 0, 'total_insurance': 0, 'total_health': 0, 'total_clothing': 0,
                'total_employer_costs': 0, 'total_profit': 0, 'employee_count': 0,
            }
        c = companies_map[cname]
        c['employees'].append(r)
        c['total_revenue'] += r['total_salary_revenue']
        c['total_basic_paid'] += r['basic_paid']
        c['total_resident_paid'] += r['resident_paid']
        c['total_overtime'] += r.get('overtime_amount', 0)
        c['total_insurance'] += r['insurance_cost']
        c['total_health'] += r['health_cost']
        c['total_clothing'] += r['clothing_cost']
        c['total_employer_costs'] += r['total_employer_costs']
        c['total_profit'] += r['profit']
        c['employee_count'] += 1

    return ok({
        'month_year': month_year,
        'employees': results,
        'companies': list(companies_map.values()),
        'summary': {
            'total_employees': len(employees),
            'total_revenue': total_revenue,
            'total_basic_paid': total_basic_paid,
            'total_resident_paid': total_resident_paid,
            'total_employer_costs': total_insurance_cost + total_health_cost + total_clothing_cost,
            'total_insurance_cost': total_insurance_cost,
            'total_health_cost': total_health_cost,
            'total_clothing_cost': total_clothing_cost,
            'total_profit': total_profit,
            'profit_per_employee': round(total_profit / len(employees), 2) if employees else 0,
        }
    })


# ==================== الفترات المالية ====================

@rest_api.route('/periods', methods=['GET'])
@login_required
def api_periods_list():
    periods = FinancialPeriod.query.order_by(FinancialPeriod.start_date.desc()).all()
    return ok([p.to_dict() for p in periods])


@rest_api.route('/periods', methods=['POST'])
@login_required
def api_period_create():
    if not current_user.has_any_role('admin', 'accountant'):
        return fail('غير مصرح لك بإنشاء فترات', 403)
    data = request.get_json(force=True, silent=True) or {}
    name = data.get('name', '')
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    if end_date <= start_date:
        return fail('تاريخ النهاية يجب أن يكون بعد تاريخ البداية')
    overlap = FinancialPeriod.query.filter(
        FinancialPeriod.start_date <= end_date,
        FinancialPeriod.end_date >= start_date
    ).first()
    if overlap:
        return fail(f'توجد فترة متداخلة: {overlap.name}')
    p = FinancialPeriod(
        name=name, period_type=data.get('period_type', 'monthly'),
        start_date=start_date, end_date=end_date,
        status='open', fiscal_year_id=data.get('fiscal_year_id'),
        notes=data.get('notes', '')
    )
    db.session.add(p)
    db.session.commit()
    return ok(p.to_dict(), 'تم إنشاء الفترة')


@rest_api.route('/periods/<int:pid>/close', methods=['POST'])
@login_required
def api_period_close(pid):
    if not current_user.has_any_role('admin', 'accountant'):
        return fail('غير مصرح لك بإغلاق الفترات', 403)
    period = FinancialPeriod.query.get_or_404(pid)
    if period.status != 'open':
        return fail('هذه الفترة ليست مفتوحة')
    period.close(current_user.id)
    db.session.commit()
    return ok(period.to_dict(), 'تم إغلاق الفترة')


@rest_api.route('/periods/<int:pid>/reopen', methods=['POST'])
@login_required
def api_period_reopen(pid):
    if not current_user.has_role('admin'):
        return fail('فقط المسؤول يمكنه إعادة فتح الفترات', 403)
    period = FinancialPeriod.query.get_or_404(pid)
    if period.status == 'locked':
        return fail('هذه الفترة مقفلة ولا يمكن فتحها')
    period.status = 'open'
    period.closed_by = None
    period.closed_at = None
    db.session.commit()
    return ok(period.to_dict(), 'تم إعادة فتح الفترة')


@rest_api.route('/periods/check', methods=['GET'])
@login_required
def api_period_check():
    """التحقق من الفترة المفتوحة لتاريخ معين"""
    date_str = request.args.get('date')
    if not date_str:
        return fail('التاريخ مطلوب')
    check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    period = FinancialPeriod.query.filter(
        FinancialPeriod.start_date <= check_date,
        FinancialPeriod.end_date >= check_date,
        FinancialPeriod.status == 'open'
    ).first()
    return ok({
        'has_open_period': period is not None,
        'period': period.to_dict() if period else None
    })


# ==================== إدارة الإجازات ====================

@rest_api.route('/leave-types', methods=['GET'])
@login_required
def api_leave_types():
    types = LeaveType.query.filter_by(is_active=True).all()
    return ok([t.to_dict() for t in types])


@rest_api.route('/leave-types', methods=['POST'])
@login_required
def api_leave_type_create():
    if not current_user.has_role('admin'):
        return fail('غير مصرح', 403)
    data = request.get_json(force=True, silent=True) or {}
    lt = LeaveType(
        name=data.get('name', ''), name_ar=data.get('name_ar', ''),
        days_per_year=int(data.get('days_per_year', 30)),
        is_paid=data.get('is_paid', True),
        max_consecutive_days=data.get('max_consecutive_days'),
    )
    db.session.add(lt)
    db.session.commit()
    return ok(lt.to_dict(), 'تم إنشاء نوع الإجازة')


@rest_api.route('/leave-balances', methods=['GET'])
@login_required
def api_leave_balances():
    year = request.args.get('year', datetime.now().year, type=int)
    employee_id = request.args.get('employee_id', type=int)

    if current_user.role == 'employee':
        emp = Employee.query.get(current_user.employee_id)
        if emp:
            employee_id = emp.id

    query = LeaveBalance.query.filter_by(year=year)
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    balances = query.all()
    return ok([b.to_dict() for b in balances])


@rest_api.route('/leave-balances/initialize', methods=['POST'])
@login_required
def api_leave_balances_init():
    """تهيئة أرصدة الإجازات لجميع الموظفين النشطين لسنة معينة"""
    if not current_user.has_role('admin'):
        return fail('غير مصرح', 403)
    data = request.get_json(force=True, silent=True) or {}
    year = data.get('year', datetime.now().year)
    leave_types = LeaveType.query.filter_by(is_active=True).all()
    employees = Employee.query.filter_by(is_active=True).all()
    count = 0
    for emp in employees:
        for lt in leave_types:
            existing = LeaveBalance.query.filter_by(employee_id=emp.id, leave_type_id=lt.id, year=year).first()
            if not existing:
                b = LeaveBalance(
                    employee_id=emp.id, leave_type_id=lt.id, year=year,
                    total_days=lt.days_per_year, used_days=0, remaining_days=lt.days_per_year
                )
                db.session.add(b)
                count += 1
    db.session.commit()
    return ok({'count': count}, f'تم تهيئة {count} رصيد')


@rest_api.route('/leave-requests', methods=['GET'])
@login_required
def api_leave_requests():
    status = request.args.get('status')
    employee_id = request.args.get('employee_id', type=int)

    if current_user.role == 'employee':
        emp = Employee.query.get(current_user.employee_id)
        if emp:
            employee_id = emp.id

    query = LeaveRequest.query
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    if status:
        query = query.filter_by(status=status)
    requests = query.order_by(LeaveRequest.created_at.desc()).all()
    return ok([r.to_dict() for r in requests])


@rest_api.route('/leave-requests', methods=['POST'])
@login_required
def api_leave_request_create():
    data = request.get_json(force=True, silent=True) or {}
    employee_id = data.get('employee_id')
    leave_type_id = data.get('leave_type_id')
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    total_days = float(data.get('total_days', 0))

    if current_user.role == 'employee':
        emp = Employee.query.get(current_user.employee_id)
        if emp:
            employee_id = emp.id
        else:
            return fail('لم يتم ربط حسابك بموظف', 400)

    if not employee_id or not leave_type_id:
        return fail('بيانات ناقصة')

    if end_date < start_date:
        return fail('تاريخ النهاية قبل تاريخ البداية')

    # التحقق من عدم التداخل مع طلبات أخرى مقبولة
    overlap = LeaveRequest.query.filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status.in_(['pending', 'approved']),
        LeaveRequest.start_date <= end_date,
        LeaveRequest.end_date >= start_date
    ).first()
    if overlap:
        return fail('توجد إجازة متداخلة مع هذا التاريخ')

    # التحقق من الرصيد
    year = start_date.year
    balance = LeaveBalance.query.filter_by(
        employee_id=employee_id, leave_type_id=leave_type_id, year=year
    ).first()
    if balance and balance.remaining_days < total_days:
        return fail(f'الرصيد غير كافٍ. المتبقي: {balance.remaining_days} يوم')

    lr = LeaveRequest(
        employee_id=employee_id, leave_type_id=leave_type_id,
        start_date=start_date, end_date=end_date,
        total_days=total_days, reason=data.get('reason', ''),
        is_paid=data.get('is_paid', True),
    )
    db.session.add(lr)
    db.session.commit()
    return ok(lr.to_dict(), 'تم إرسال طلب الإجازة')


@rest_api.route('/leave-requests/<int:rid>/approve', methods=['POST'])
@login_required
def api_leave_request_approve(rid):
    if not current_user.has_any_role('admin', 'supervisor'):
        return fail('غير مصرح لك بالموافقة', 403)
    lr = LeaveRequest.query.get_or_404(rid)
    if lr.status != 'pending':
        return fail('هذا الطلب ليس قيد المراجعة')
    lr.approve(current_user.id)

    # خصم من الرصيد
    year = lr.start_date.year
    balance = LeaveBalance.query.filter_by(
        employee_id=lr.employee_id, leave_type_id=lr.leave_type_id, year=year
    ).first()
    if balance:
        balance.use_days(lr.total_days)

    db.session.commit()
    return ok(lr.to_dict(), 'تمت الموافقة على الإجازة')


@rest_api.route('/leave-requests/<int:rid>/reject', methods=['POST'])
@login_required
def api_leave_request_reject(rid):
    if not current_user.has_any_role('admin', 'supervisor'):
        return fail('غير مصرح لك بالرفض', 403)
    lr = LeaveRequest.query.get_or_404(rid)
    if lr.status != 'pending':
        return fail('هذا الطلب ليس قيد المراجعة')
    data = request.get_json(force=True, silent=True) or {}
    lr.reject(current_user.id, data.get('reason', ''))
    db.session.commit()
    return ok(lr.to_dict(), 'تم رفض الإجازة')


# ==================== مستخدمي الموظفين ====================

@rest_api.route('/employee/my-profile', methods=['GET'])
@login_required
def api_employee_profile():
    """عرض الملف الشخصي للموظف"""
    if current_user.role != 'employee':
        return fail('هذه للموظفين فقط', 403)
    emp = Employee.query.get(current_user.employee_id)
    if not emp:
        return fail('لم يتم ربط حسابك بموظف', 404)
    return ok({
        'id': emp.id, 'name': emp.name, 'job_title': emp.job_title,
        'phone': emp.phone, 'region': emp.region,
        'company_id': emp.company_id,
        'company_name': emp.company.name if emp.company else '',
        'is_resident': emp.is_resident,
        'salary': emp.salary, 'total_salary': emp.total_salary,
        'basic_salary': emp.basic_salary,
        'user': current_user.to_dict(),
    })


@rest_api.route('/employee/my-attendance', methods=['GET'])
@login_required
def api_employee_my_attendance():
    """عرض حضور الموظف"""
    if current_user.role != 'employee':
        return fail('هذه للموظفين فقط', 403)
    emp = Employee.query.get(current_user.employee_id)
    if not emp:
        return fail('لم يتم ربط حسابك بموظف', 404)
    month = request.args.get('month')
    year = request.args.get('year', datetime.now().year, type=int)
    query = Attendance.query.filter_by(employee_id=emp.id)
    if month:
        from sqlalchemy import extract
        query = query.filter(extract('month', Attendance.date) == int(month))
    query = query.filter(extract('year', Attendance.date) == year)
    records = query.order_by(Attendance.date.desc()).all()
    return ok([{
        'id': r.id, 'date': r.date.strftime('%Y-%m-%d'),
        'status': r.attendance_status,
        'status_name': {'present': 'حاضر', 'late': 'متأخر', 'sick': 'مرضي', 'absent': 'غائب', 'annual_leave': 'إجازة'}.get(r.attendance_status, r.attendance_status),
        'late_minutes': r.late_minutes,
        'notes': r.notes or '',
    } for r in records])


@rest_api.route('/employee/my-salaries', methods=['GET'])
@login_required
def api_employee_my_salaries():
    """عرض رواتب الموظف"""
    if current_user.role != 'employee':
        return fail('هذه للموظفين فقط', 403)
    emp = Employee.query.get(current_user.employee_id)
    if not emp:
        return fail('لم يتم ربط حسابك بموظف', 404)
    salaries = Salary.query.filter_by(employee_id=emp.id).order_by(Salary.month_year.desc()).all()
    return ok([{
        'id': s.id, 'month_year': s.month_year,
        'basic_salary_amount': s.basic_salary_amount,
        'overtime_amount': s.overtime_amount,
        'advance_amount': s.advance_amount,
        'deduction_amount': s.deduction_amount,
        'penalty_amount': s.penalty_amount,
        'total_salary': s.total_salary,
        'is_paid': s.is_paid,
        'paid_date': s.paid_date.strftime('%Y-%m-%d') if s.paid_date else None,
    } for s in salaries])


@rest_api.route('/employee/my-leaves', methods=['GET'])
@login_required
def api_employee_my_leaves():
    """عرض إجازات الموظف"""
    if current_user.role != 'employee':
        return fail('هذه للموظفين فقط', 403)
    emp = Employee.query.get(current_user.employee_id)
    if not emp:
        return fail('لم يتم ربط حسابك بموظف', 404)
    year = request.args.get('year', datetime.now().year, type=int)
    balances = LeaveBalance.query.filter_by(employee_id=emp.id, year=year).all()
    requests = LeaveRequest.query.filter_by(employee_id=emp.id).order_by(LeaveRequest.created_at.desc()).all()
    return ok({
        'balances': [b.to_dict() for b in balances],
        'requests': [r.to_dict() for r in requests],
    })


@rest_api.route('/employee/change-password', methods=['POST'])
@login_required
def api_employee_change_password():
    """تغيير كلمة مرور الموظف"""
    from werkzeug.security import generate_password_hash, check_password_hash
    data = request.get_json(force=True, silent=True) or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if not old_password or not new_password:
        return fail('كلمة المرور القديمة والجديدة مطلوبتين')
    if len(new_password) < 4:
        return fail('كلمة المرور الجديدة يجب أن تكون 4 أحرف على الأقل')
    user = User.query.get(current_user.id)
    if not check_password_hash(user.password, old_password):
        return fail('كلمة المرور القديمة غير صحيحة')
    user.password = generate_password_hash(new_password)
    db.session.commit()
    return ok(None, 'تم تغيير كلمة المرور بنجاح')


@rest_api.route('/employee/my-transactions', methods=['GET'])
@login_required
def api_employee_my_transactions():
    """عرض المعاملات المالية للموظف"""
    if current_user.role != 'employee':
        return fail('هذه للموظفين فقط', 403)
    emp = Employee.query.get(current_user.employee_id)
    if not emp:
        return fail('لم يتم ربط حسابك بموظف', 404)
    txs = FinancialTransaction.query.filter_by(employee_id=emp.id).order_by(FinancialTransaction.date.desc()).all()
    return ok([t.to_dict() for t in txs])


@rest_api.route('/employee/my-evaluations', methods=['GET'])
@login_required
def api_employee_my_evaluations():
    """عرض تقييمات الموظف"""
    if current_user.role != 'employee':
        return fail('هذه للموظفين فقط', 403)
    emp = Employee.query.get(current_user.employee_id)
    if not emp:
        return fail('لم يتم ربط حسابك بموظف', 404)
    evals = Evaluation.query.filter_by(employee_id=emp.id).order_by(Evaluation.date.desc()).all()
    return ok([{
        'id': e.id, 'date': e.date.strftime('%Y-%m-%d') if e.date else None,
        'score': e.score, 'comments': e.comments or '',
        'evaluation_type': e.evaluation_type,
        'evaluator_name': e.evaluator.full_name if e.evaluator else '',
    } for e in evals])
