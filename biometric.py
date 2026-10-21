"""محرك أجهزة البصمة (ZKTeco).

يحتوي على:
- إدارة الإعدادات (الوردية، مهلة التأخير، أيام العمل...).
- استقبال السجلات الخام من الأجهزة (Push/ADMS أو وكيل محلي).
- ربط رقم البصمة (PIN) بالموظف في النظام.
- تحويل السجلات الخام إلى سجلات حضور (Attendance) التي تعتمد عليها احتساب الرواتب.
"""

from datetime import datetime, date, timedelta, time as dtime

from models import (
    db, Employee, Attendance, Company, LeaveRequest, LeaveType,
    BiometricDevice, BiometricLog, BiometricSetting,
)

# ==================== الإعدادات ====================

DEFAULT_SETTINGS = [
    ('shift_start', 'بداية الدوام', '08:00', 'text',
     'وقت بدء الدوام الرسمي - يُستخدم لحساب التأخير'),
    ('shift_end', 'نهاية الدوام', '17:00', 'text',
     'نهاية الدوام الرسمي'),
    ('late_grace_minutes', 'مهلة التأخير', '15', 'number',
     'عدد الدقائق التي لا يُحتسب بعدها الموظف متأخراً'),
    ('work_days', 'أيام العمل', '0,1,2,3,5,6', 'text',
     'أيام العمل مفصولة بفاصلة: 0=الإثنين ... 6=الأحد (الجمعة=4 وهي عطلة)'),
    ('auto_absent', 'تسجيل الغياب تلقائياً', 'false', 'bool',
     'إنشاء سجلات غياب للأيام التي لا يوجد فيها بصمة'),
    ('skip_existing', 'عدم تعديل الحضور اليدوي', 'true', 'bool',
     'عند وجود سجل حضور مُدخل يدوياً لا يتم استبداله من البصمة'),
    ('overwrite_status', 'تحديث حالة الحضور عند البصمة', 'true', 'bool',
     'تحديث الحالة (حاضر/متأخر) للسجل الموجود مسبقاً مع الحفاظ على الأوقات'),
    ('ingest_api_key', 'مفتاح استقبال السجلات', '', 'text',
     'مفتاح سري يستعمله الوكيل المحلي أو الجهاز عند دفع السجلات (اتركه فارغاً للسماح)'),
]


def get_setting(key, default=None):
    """قراءة إعداد بصمة مع القيمة الافتراضية"""
    row = BiometricSetting.query.filter_by(setting_key=key).first()
    if row and row.value is not None:
        return row.value
    if default is not None:
        return default
    for k, _n, v, _t, _d in DEFAULT_SETTINGS:
        if k == key:
            return v
    return ''


def get_bool_setting(key, default=False):
    val = str(get_setting(key, '')).strip().lower()
    if val in ('1', 'true', 'yes', 'on'):
        return True
    if val in ('0', 'false', 'no', 'off'):
        return False
    return default


def set_setting(key, value):
    """حفظ إعداد بصمة"""
    row = BiometricSetting.query.filter_by(setting_key=key).first()
    if not row:
        name = key
        vtype = 'text'
        desc = ''
        for k, n, _v, t, d in DEFAULT_SETTINGS:
            if k == key:
                name, vtype, desc = n, t, d
        row = BiometricSetting(setting_key=key, setting_name=name, value_type=vtype, description=desc)
        db.session.add(row)
    row.value = str(value)
    db.session.commit()
    return row


def init_default_biometric_settings():
    """تهيئة إعدادات البصمة الافتراضية عند أول تشغيل"""
    created = 0
    for key, name, value, vtype, desc in DEFAULT_SETTINGS:
        if not BiometricSetting.query.filter_by(setting_key=key).first():
            db.session.add(BiometricSetting(
                setting_key=key, setting_name=name, value=value,
                value_type=vtype, description=desc,
            ))
            created += 1
    if created:
        db.session.commit()
    return created


def get_shift_times():
    """إرجاع (بداية الدوام، نهاية الدوام، مهلة التأخير بالدقائق)"""
    def _parse(value, fallback):
        try:
            parts = str(value).split(':')
            return dtime(int(parts[0]), int(parts[1]), 0)
        except Exception:
            return fallback

    shift_start = _parse(get_setting('shift_start', '08:00'), dtime(8, 0))
    shift_end = _parse(get_setting('shift_end', '17:00'), dtime(17, 0))
    try:
        grace = int(float(get_setting('late_grace_minutes', '15') or 0))
    except (TypeError, ValueError):
        grace = 15
    return shift_start, shift_end, grace


def get_work_days():
    """أيام العمل (أرقام weekday)"""
    raw = str(get_setting('work_days', '0,1,2,3,5,6') or '')
    days = set()
    for part in raw.split(','):
        part = part.strip()
        if part.isdigit():
            days.add(int(part))
    return days or {0, 1, 2, 3, 5, 6}


def is_work_day(d):
    """هل اليوم يوم عمل حسب الإعدادات"""
    return d.weekday() in get_work_days()


# ==================== ربط الموظف بالجهاز ====================

def resolve_employee(pin, card_number=None):
    """إيجاد الموظف من رقم البصمة (PIN) أو رقم البطاقة.
    الأولوية: biometric_pin ثم كود الموظف ثم رقم البطاقة.
    """
    if pin is None:
        return None
    pin_str = str(pin).strip()
    if not pin_str:
        return None

    emp = Employee.query.filter(Employee.biometric_pin == pin_str).first()
    if emp:
        return emp

    emp = Employee.query.filter(Employee.code == pin_str).first()
    if emp:
        return emp

    if card_number:
        card_str = str(card_number).strip()
        if card_str:
            emp = Employee.query.filter(Employee.card_number == card_str).first()
            if emp:
                return emp
    return None


# ==================== استقبال السجلات ====================

ICLOCK_LOG_TYPES = {
    '0': 'in', '1': 'out', '2': 'unknown', '3': 'unknown', '4': 'in',
    '5': 'unknown', '6': 'unknown', '7': 'unknown', '8': 'unknown', '9': 'unknown',
}

ICLOCK_VERIFY_MODES = {
    '0': 'password', '1': 'fp', '2': 'card', '3': 'card', '4': 'face',
    '5': 'palm', '6': 'finger_vein', '15': 'face', '16': 'card',
}

DATETIME_FORMATS = [
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%d/%m/%Y %H:%M:%S',
    '%d/%m/%Y %H:%M',
    '%m/%d/%Y %H:%M:%S',
    '%m/%d/%Y %H:%M',
    '%Y-%m-%dT%H:%M:%S',
    '%Y/%m/%d %H:%M:%S',
    '%Y-%m-%d',
    '%H:%M:%S',
    '%H:%M',
]


def parse_datetime(value):
    """تحويل نص إلى datetime مع دعم عدة صيغ"""
    if isinstance(value, datetime):
        return value
    if isinstance(value, dtime):
        return datetime.combine(date.today(), value)
    if isinstance(value, date):
        return datetime.combine(value, dtime(0, 0))
    text = str(value or '').strip()
    if not text:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    # تواريخ Excel كأرقام تسلسلية
    if text.replace('.', '', 1).isdigit():
        try:
            serial = float(text)
            if serial > 20000:
                return datetime(1899, 12, 30) + timedelta(days=serial)
        except Exception:
            pass
    return None


def combine_date_time(date_value, time_value=None):
    """دمج قيمة تاريخ (ويوماً) مع قيمة وقت في datetime واحد"""
    base = parse_datetime(date_value)
    tv = parse_datetime(time_value)
    if base and tv:
        if base.time() == dtime(0, 0) and tv.time() != dtime(0, 0):
            return datetime.combine(base.date(), tv.time())
        if tv.time() != dtime(0, 0) and base.time() != dtime(0, 0):
            return datetime.combine(base.date(), base.time())
        return datetime.combine(base.date(), tv.time())
    if base:
        return base
    if tv:
        return datetime.combine(date.today(), tv.time())
    return None


def parse_iclock_lines(text):
    """تحليل نص سجلات جهاز ZK (صيغة ADMS/ICLOCK) إلى قائمة سجلات.
    كل سطر: PIN, DateTime, LogType, VerifyType, WorkCode, ...
    """
    logs = []
    for line in str(text or '').splitlines():
        line = line.strip()
        if not line or line.lower() in ('ok', 'none', 'no data'):
            continue
        if line.startswith('ATTLOG') or line.startswith('ATTDATA'):
            continue
        parts = [p.strip() for p in line.replace(';', '\t').split('\t')]
        parts = [p for p in parts if p != ''] if len(parts) > 1 else parts
        if len(parts) < 2:
            continue
        pin = parts[0]
        dt = parse_datetime(parts[1])
        if not dt or not pin:
            continue
        log_type = ICLOCK_LOG_TYPES.get(parts[2] if len(parts) > 2 else '0', 'unknown')
        mode = ICLOCK_VERIFY_MODES.get(parts[3] if len(parts) > 3 else '1', None)
        work_code = parts[4] if len(parts) > 4 and parts[4] else None
        logs.append({
            'pin': pin,
            'time': dt,
            'type': log_type,
            'mode': mode,
            'work_code': work_code,
            'raw': line,
        })
    return logs


def ingest_logs(device, logs, source='agent'):
    """حفظ السجلات الخام في قاعدة البيانات (منع التكرار).
    يُرجع (عدد المضاف، عدد المكرر، قائمة الـ PIN غير المرتبطة).
    """
    added = 0
    duplicated = 0
    unmapped = set()

    for item in logs or []:
        pin = str(item.get('pin') or item.get('user_id') or '').strip()
        dt = item.get('time') or item.get('datetime') or item.get('log_time')
        if isinstance(dt, str):
            dt = parse_datetime(dt)
        if not pin or not dt:
            continue

        log_type = str(item.get('type') or item.get('log_type') or 'unknown').lower()
        if log_type in ('checkin', 'check_in', '0'):
            log_type = 'in'
        elif log_type in ('checkout', 'check_out', '1'):
            log_type = 'out'
        elif log_type not in ('in', 'out'):
            log_type = 'unknown'

        mode = item.get('mode') or item.get('verify_mode')
        if mode:
            mode = ICLOCK_VERIFY_MODES.get(str(mode), str(mode))
        work_code = item.get('work_code') or item.get('workcode')
        card = item.get('card') or item.get('card_number')

        exists = BiometricLog.query.filter_by(
            device_id=device.id, pin=pin, log_time=dt, log_type=log_type
        ).first()
        if exists:
            duplicated += 1
            continue

        employee = resolve_employee(pin, card)
        if not employee:
            unmapped.add(pin)

        db.session.add(BiometricLog(
            device_id=device.id,
            employee_id=employee.id if employee else None,
            pin=pin,
            card_number=str(card) if card else None,
            log_time=dt,
            log_date=dt.date(),
            log_type=log_type,
            verify_mode=mode,
            work_code=str(work_code) if work_code else None,
            notes=item.get('notes') or (f'مصدر: {source}' if source else None),
            raw_data=item.get('raw') or json_dumps(item),
        ))
        added += 1

    db.session.commit()
    return added, duplicated, sorted(unmapped)


def json_dumps(data):
    """تسلسل بسيط لتفادي استيراد json في كل مكان"""
    import json
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return str(data)


# ==================== تحويل السجلات إلى حضور ====================

def _approved_leave_status(employee, day):
    """حالة الإجازة المعتمدة للموظف في يوم معين أو None"""
    leaves = LeaveRequest.query.filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status == 'approved',
        LeaveRequest.start_date <= day,
        LeaveRequest.end_date >= day,
    ).all()
    for lv in leaves:
        ltype = lv.leave_type
        name = (ltype.name_ar if ltype else '') or ''
        key = (ltype.name if ltype else '') or ''
        if not lv.is_paid or 'unpaid' in key.lower() or 'بدون' in name:
            return 'unpaid_leave'
        if 'sick' in key.lower() or 'مرضية' in name:
            return 'sick'
        return 'annual_leave'
    return None


def process_logs(start_date=None, end_date=None, device_id=None, force=False, user_id=None):
    """تحويل السجلات الخام إلى سجلات حضور.

    يعيد قاموساً يحتوي على ملخص العملية وسجلات غير مرتبطة بالموظفين.
    """
    shift_start, shift_end, grace = get_shift_times()
    skip_existing = get_bool_setting('skip_existing', True)
    overwrite_status = get_bool_setting('overwrite_status', True)

    q = BiometricLog.query.filter_by(is_processed=False)
    if start_date:
        q = q.filter(BiometricLog.log_date >= start_date)
    if end_date:
        q = q.filter(BiometricLog.log_date <= end_date)
    if device_id:
        q = q.filter(BiometricLog.device_id == device_id)
    logs = q.order_by(BiometricLog.log_time.asc()).all()

    groups = {}
    unmapped = set()
    for log in logs:
        emp_id = log.employee_id
        if not emp_id:
            emp = resolve_employee(log.pin, log.card_number)
            if emp:
                log.employee_id = emp.id
                emp_id = emp.id
            else:
                unmapped.add(log.pin)
                continue
        key = (emp_id, log.log_date)
        groups.setdefault(key, []).append(log)

    created = 0
    updated = 0
    skipped = 0
    leave_days = 0
    now = datetime.utcnow()

    for (emp_id, day), day_logs in groups.items():
        employee = Employee.query.get(emp_id)
        if not employee or not employee.is_active:
            for lg in day_logs:
                lg.is_processed = True
                lg.processed_at = now
                lg.notes = 'الموظف غير نشط - تم تجاهل السجل'
            skipped += 1
            continue

        leave_status = _approved_leave_status(employee, day)
        if leave_status:
            for lg in day_logs:
                lg.is_processed = True
                lg.processed_at = now
                lg.notes = f'إجازة معتمدة ({leave_status}) - لم يتم تعديل الحضور'
            leave_days += 1
            continue

        times = [lg.log_time for lg in day_logs if lg.log_time]
        if not times:
            skipped += 1
            continue
        check_in = min(times)
        check_out = max(times)

        late_minutes = 0
        status = 'present'
        ref = datetime.combine(day, shift_start)
        deadline = ref + timedelta(minutes=grace)
        if check_in > deadline:
            late_minutes = int((check_in - deadline).total_seconds() // 60)
            status = 'late'
        if check_in > datetime.combine(day, shift_end):
            status = 'absent'

        existing = Attendance.query.filter_by(employee_id=emp_id, date=day).first()
        device_name = day_logs[0].device.name if day_logs[0].device else 'جهاز البصمة'
        note = f'بصمة: {device_name}'

        if existing:
            if skip_existing and not overwrite_status:
                for lg in day_logs:
                    lg.is_processed = True
                    lg.processed_at = now
                    lg.notes = 'يوجد سجل حضور يدوي - تم تجاهل البصمة'
                skipped += 1
                continue
            existing.check_in_time = check_in.time()
            existing.check_out_time = check_out.time()
            existing.late_minutes = late_minutes
            if overwrite_status or existing.attendance_status in ('absent', ''):
                existing.attendance_status = status
            if not existing.notes:
                existing.notes = note
            updated += 1
        else:
            db.session.add(Attendance(
                employee_id=emp_id,
                date=day,
                attendance_type='individual',
                attendance_status=status,
                late_minutes=late_minutes,
                check_in_time=check_in.time(),
                check_out_time=check_out.time(),
                notes=note,
                created_by=user_id,
            ))
            created += 1

        for lg in day_logs:
            lg.is_processed = True
            lg.processed_at = now
            lg.notes = f'تم التحويل إلى حضور ({status})'

    db.session.commit()

    return {
        'processed_logs': len(logs),
        'created_records': created,
        'updated_records': updated,
        'skipped': skipped,
        'leave_days': leave_days,
        'unmapped_pins': sorted(unmapped),
        'unmapped_count': len(unmapped),
    }


def mark_absent_days(start_date, end_date, company_id=None, user_id=None):
    """إنشاء سجلات غياب للأيام التي لا يوجد فيها بصمة ولا إجازة معتمدة"""
    if end_date < start_date:
        return {'error': 'تاريخ النهاية يجب أن يكون بعد تاريخ البداية'}

    emp_q = Employee.query.filter_by(is_active=True)
    if company_id:
        emp_q = emp_q.filter_by(company_id=company_id)
    employees = emp_q.all()

    created = 0
    skipped_leave = 0
    day = start_date
    while day <= end_date:
        if is_work_day(day):
            for emp in employees:
                exists = Attendance.query.filter_by(employee_id=emp.id, date=day).first()
                if exists:
                    continue
                if _approved_leave_status(emp, day):
                    skipped_leave += 1
                    continue
                db.session.add(Attendance(
                    employee_id=emp.id,
                    date=day,
                    attendance_type='individual',
                    attendance_status='absent',
                    notes='غياب - لم تُرسل بصمة',
                    created_by=user_id,
                ))
                created += 1
        day += timedelta(days=1)

    db.session.commit()
    return {'created': created, 'leave_days_skipped': skipped_leave, 'employees': len(employees)}


# ==================== السحب من الجهاز ====================

def pull_from_device(device, timeout=10):
    """سحب السجلات من جهاز ZKTeco عبر TCP (يحتاج مكتبة pyzk).
    يعمل فقط إذا كان الخادم نفسه يصل إلى شبكة الجهاز.
    """
    if not device.ip_address:
        return {'success': False, 'message': 'لا يوجد عنوان IP للجهاز'}
    try:
        from pyzk import ZK, const as zkconst
    except ImportError:
        return {
            'success': False,
            'message': 'مكتبة pyzk غير مثبتة على الخادم. استخدم الوكيل المحلي على جهاز المكتب '
                       '(tools/zk_sync_agent.py) أو ثبّت: pip install pyzk',
        }

    try:
        zk = ZK(device.ip_address, port=device.port or 4370,
                timeout=timeout, password=device.password or '', force_udp=False)
        conn = zk.connect()
        if conn:
            logs = []
            for att in zk.get_attendance():
                ts = getattr(att, 'timestamp', None)
                if not ts:
                    continue
                logs.append({
                    'pin': str(getattr(att, 'uid', '') or ''),
                    'time': ts,
                    'type': 'out' if getattr(att, 'log_type', None) == 1 else 'in',
                    'mode': 'fp',
                    'raw': str(att),
                })
            zk.disconnect()
            added, dup, unmapped = ingest_logs(device, logs, source='pull')
            device.last_sync_at = datetime.utcnow()
            device.last_sync_count = added
            device.last_sync_message = f'تم سحب {added} سجل (مكرر: {dup})'
            db.session.commit()
            return {
                'success': True,
                'fetched': len(logs),
                'added': added,
                'duplicated': dup,
                'unmapped': unmapped,
                'message': device.last_sync_message,
            }
        return {'success': False, 'message': 'تعذر الاتصال بالجهاز (تحقق من IP والمنفذ وكلمة المرور)'}
    except Exception as e:
        return {'success': False, 'message': f'خطأ أثناء السحب: {e}'}


# ==================== حالة النظام ====================

def status_summary():
    """ملخص حالة أجهزة البصمة"""
    devices = BiometricDevice.query.all()
    total_logs = BiometricLog.query.count()
    unprocessed = BiometricLog.query.filter_by(is_processed=False).count()
    unmapped = db.session.query(BiometricLog.pin).filter(
        BiometricLog.employee_id.is_(None), BiometricLog.is_processed == False
    ).distinct().all()
    linked = Employee.query.filter(Employee.biometric_pin.isnot(None)).count()

    return {
        'devices_count': len(devices),
        'active_devices': len([d for d in devices if d.is_active]),
        'total_logs': total_logs,
        'unprocessed_logs': unprocessed,
        'unmapped_pins': [r[0] for r in unmapped],
        'linked_employees': linked,
        'devices': [d.to_dict() for d in devices],
    }
