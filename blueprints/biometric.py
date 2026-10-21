"""مسارات أجهزة البصمة (ZKTeco) — تسجيل الأجهزة، استقبال السجلات، المعالجة، الاستيراد."""

import io
from datetime import datetime, date, timedelta

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from models import (
    db, Employee, Attendance, Company, BiometricDevice, BiometricLog, BiometricSetting,
)
import biometric as bio

biometric_bp = Blueprint('biometric', __name__, url_prefix='/api/biometric')


def ok(data=None, message='success'):
    return jsonify({'success': True, 'message': message, 'data': data})


def fail(message='error', status=400):
    return jsonify({'success': False, 'message': message}), status


def _is_admin():
    return current_user.is_authenticated and current_user.has_any_role('admin')


# ==================== الأجهزة ====================

@biometric_bp.route('/devices', methods=['GET'])
@login_required
def devices_list():
    devices = BiometricDevice.query.order_by(BiometricDevice.name).all()
    return ok([d.to_dict() for d in devices])


@biometric_bp.route('/devices', methods=['POST'])
@login_required
def device_create():
    if not _is_admin():
        return fail('غير مصرح لك بإدارة الأجهزة', 403)
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return fail('اسم الجهاز مطلوب')
    sn = (data.get('serial_number') or '').strip() or None
    if sn and BiometricDevice.query.filter_by(serial_number=sn).first():
        return fail('يوجد جهاز مسجل بنفس الرقم التسلسلي')
    device = BiometricDevice(
        name=name,
        serial_number=sn,
        ip_address=(data.get('ip_address') or '').strip() or None,
        port=int(data.get('port') or 4370),
        password=(data.get('password') or '').strip() or None,
        api_key=(data.get('api_key') or '').strip() or None,
        direction=data.get('direction') or 'pull',
        company_id=data.get('company_id') or None,
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(device)
    db.session.commit()
    return ok(device.to_dict(), 'تم إضافة الجهاز')


@biometric_bp.route('/devices/<int:did>', methods=['PUT'])
@login_required
def device_update(did):
    if not _is_admin():
        return fail('غير مصرح لك بتعديل الأجهزة', 403)
    device = BiometricDevice.query.get_or_404(did)
    data = request.get_json(force=True, silent=True) or {}
    if 'name' in data and data['name']:
        device.name = data['name'].strip()
    if 'serial_number' in data:
        device.serial_number = (data['serial_number'] or '').strip() or None
    if 'ip_address' in data:
        device.ip_address = (data['ip_address'] or '').strip() or None
    if 'port' in data:
        device.port = int(data['port'] or 4370)
    if 'password' in data:
        device.password = (data['password'] or '').strip() or None
    if 'api_key' in data:
        device.api_key = (data['api_key'] or '').strip() or None
    if 'direction' in data:
        device.direction = data['direction'] or 'pull'
    if 'company_id' in data:
        device.company_id = data['company_id'] or None
    if 'is_active' in data:
        device.is_active = bool(data['is_active'])
    db.session.commit()
    return ok(device.to_dict(), 'تم تحديث الجهاز')


@biometric_bp.route('/devices/<int:did>', methods=['DELETE'])
@login_required
def device_delete(did):
    if not _is_admin():
        return fail('غير مصرح لك بحذف الأجهزة', 403)
    device = BiometricDevice.query.get_or_404(did)
    db.session.delete(device)
    db.session.commit()
    return ok(None, 'تم حذف الجهاز')


@biometric_bp.route('/devices/<int:did>/pull', methods=['POST'])
@login_required
def device_pull(did):
    device = BiometricDevice.query.get_or_404(did)
    result = bio.pull_from_device(device)
    return (ok(result.get('added', 0), result.get('message', '')) if result.get('success')
            else fail(result.get('message', 'تعذر السحب'), 400))


# ==================== استقبال السجلات (الوكيل المحلي / Push) ====================

def _check_api_key():
    """التحقق من مفتاح الاستقبال (إن كان مضبوطاً)"""
    expected = str(bio.get_setting('ingest_api_key', '') or '').strip()
    if not expected:
        return True
    provided = (request.headers.get('X-API-Key') or
                request.args.get('api_key') or
                (request.get_json(silent=True) or {}).get('api_key') or '')
    return str(provided).strip() == expected


def _get_or_create_device(payload):
    """إنشاء/تحديد الجهاز بناءً على الرقم التسلسلي"""
    sn = str(payload.get('serial_number') or payload.get('sn') or '').strip()
    name = (payload.get('device_name') or payload.get('name') or '').strip() or (sn or 'جهاز بصمة')
    device = None
    if sn:
        device = BiometricDevice.query.filter_by(serial_number=sn).first()
    if not device:
        device = BiometricDevice(name=name, serial_number=sn or None, direction='push')
        db.session.add(device)
        db.session.flush()
    elif payload.get('device_name'):
        device.name = payload['device_name']
    device.last_heartbeat = datetime.utcnow()
    db.session.commit()
    return device


@biometric_bp.route('/ingest', methods=['POST'])
def ingest():
    """استقبال سجلات بصمة من الوكيل المحلي أو أي برنامج آخر"""
    if not _check_api_key():
        return fail('مفتاح الاستقبال غير صحيح', 401)
    data = request.get_json(force=True, silent=True) or {}
    device_payload = data.get('device') or {}
    device = _get_or_create_device({
        'serial_number': device_payload.get('serial_number') or data.get('serial_number'),
        'device_name': device_payload.get('name') or data.get('device_name'),
    })
    logs = data.get('logs') or []
    added, duplicated, unmapped = bio.ingest_logs(device, logs, source=data.get('source') or 'agent')
    device.last_sync_at = datetime.utcnow()
    device.last_sync_count = added
    device.last_sync_message = f'استُلم {added} سجل (مكرر {duplicated})'
    db.session.commit()
    return ok({
        'added': added,
        'duplicated': duplicated,
        'unmapped_pins': unmapped,
        'device_id': device.id,
    }, device.last_sync_message)


# ==================== بروتوكول ADMS / ICLOCK (دفع من الجهاز) ====================

@biometric_bp.route('/iclock/heartbeat', methods=['GET', 'POST'])
def iclock_heartbeat():
    """نبض الجهاز - يسجل آخر اتصال"""
    sn = request.args.get('SN') or request.args.get('sn') or ''
    if sn:
        device = BiometricDevice.query.filter_by(serial_number=sn).first()
        if device:
            device.last_heartbeat = datetime.utcnow()
            db.session.commit()
    return 'OK', 200, {'Content-Type': 'text/plain'}


@biometric_bp.route('/iclock/cdata', methods=['GET', 'POST'])
def iclock_cdata():
    """استقبال/طلب السجلات بصيغة ADMS"""
    if request.method == 'POST':
        if not _check_api_key():
            return 'FAIL', 401, {'Content-Type': 'text/plain'}
        body = request.get_data(as_text=True)
        sn = request.args.get('SN') or request.args.get('sn') or ''
        logs = bio.parse_iclock_lines(body)
        if logs:
            device = _get_or_create_device({
                'serial_number': sn,
                'device_name': request.args.get('name') or '',
            })
            added, duplicated, unmapped = bio.ingest_logs(device, logs, source='iclock')
            device.last_sync_at = datetime.utcnow()
            device.last_sync_count = added
            device.last_sync_message = f'استُلم {added} سجل (مكرر {duplicated})'
            db.session.commit()
        return 'OK', 200, {'Content-Type': 'text/plain'}

    return 'OK', 200, {'Content-Type': 'text/plain'}


@biometric_bp.route('/iclock/getrequest', methods=['GET'])
def iclock_getrequest():
    """أوامر للجهاز - نطلب تزامن الوقت فقط"""
    sn = request.args.get('SN') or request.args.get('sn') or ''
    if sn:
        device = BiometricDevice.query.filter_by(serial_number=sn).first()
        if device:
            device.last_heartbeat = datetime.utcnow()
            db.session.commit()
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    commands = f'C:1:DATA UPDATE USERINFO PIN=USERINFO\t{now}\n'
    return commands, 200, {'Content-Type': 'text/plain'}


@biometric_bp.route('/iclock/devicecmd', methods=['GET'])
def iclock_devicecmd():
    return '', 200, {'Content-Type': 'text/plain'}


# ==================== المعالجة والتحويل ====================

@biometric_bp.route('/process', methods=['POST'])
@login_required
def process():
    """تحويل السجلات الخام إلى سجلات حضور"""
    data = request.get_json(force=True, silent=True) or {}
    sd = data.get('start_date')
    ed = data.get('end_date')
    start_date = bio.parse_datetime(sd).date() if sd else None
    end_date = bio.parse_datetime(ed).date() if ed else None
    if start_date and end_date and end_date < start_date:
        return fail('تاريخ النهاية يجب أن يكون بعد تاريخ البداية')
    result = bio.process_logs(
        start_date=start_date,
        end_date=end_date,
        device_id=data.get('device_id'),
        force=bool(data.get('force')),
        user_id=current_user.id,
    )
    return ok(result, 'تمت المعالجة')


@biometric_bp.route('/mark-absent', methods=['POST'])
@login_required
def mark_absent():
    """إنشاء سجلات غياب للأيام التي لا يوجد فيها بصمة"""
    data = request.get_json(force=True, silent=True) or {}
    sd = data.get('start_date')
    ed = data.get('end_date')
    start_date = bio.parse_datetime(sd).date() if sd else None
    end_date = bio.parse_datetime(ed).date() if ed else None
    if not start_date or not end_date:
        return fail('يجب تحديد تاريخ البداية وتاريخ النهاية')
    result = bio.mark_absent_days(
        start_date, end_date,
        company_id=data.get('company_id'),
        user_id=current_user.id,
    )
    if result.get('error'):
        return fail(result['error'])
    return ok(result, f'تم إنشاء {result["created"]} سجل غياب')


# ==================== السجلات الخام ====================

@biometric_bp.route('/logs', methods=['GET'])
@login_required
def logs_list():
    q = BiometricLog.query
    device_id = request.args.get('device_id')
    if device_id:
        q = q.filter(BiometricLog.device_id == int(device_id))
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if date_from:
        d = bio.parse_datetime(date_from)
        if d:
            q = q.filter(BiometricLog.log_date >= d.date())
    if date_to:
        d = bio.parse_datetime(date_to)
        if d:
            q = q.filter(BiometricLog.log_date <= d.date())
    if request.args.get('unprocessed') == '1':
        q = q.filter(BiometricLog.is_processed == False)
    search = (request.args.get('search') or '').strip()
    if search:
        q = q.join(Employee, isouter=True).filter(
            db.or_(Employee.name.ilike(f'%{search}%'),
                   Employee.code.ilike(f'%{search}%'),
                   BiometricLog.pin.ilike(f'%{search}%'))
        )
    page = int(request.args.get('page') or 1)
    per_page = min(int(request.args.get('per_page') or 100), 500)
    total = q.count()
    logs = q.order_by(BiometricLog.log_time.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return ok({
        'logs': [l.to_dict() for l in logs],
        'total': total,
        'page': page,
        'per_page': per_page,
    })


# ==================== ربط الموظفين ====================

@biometric_bp.route('/employee-links', methods=['GET'])
@login_required
def employee_links():
    """قائمة الموظفين مع أرقام البصمة"""
    search = (request.args.get('search') or '').strip()
    q = Employee.query.filter_by(is_active=True)
    if search:
        q = q.filter(db.or_(Employee.name.ilike(f'%{search}%'), Employee.code.ilike(f'%{search}%')))
    emps = q.order_by(Employee.name).limit(500).all()
    return ok([{
        'id': e.id,
        'name': e.name,
        'code': e.code,
        'card_number': e.card_number or '',
        'biometric_pin': e.biometric_pin or '',
        'company_name': e.company.name if e.company else '',
    } for e in emps])


@biometric_bp.route('/employee-links/<int:emp_id>', methods=['PUT'])
@login_required
def employee_link_update(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    data = request.get_json(force=True, silent=True) or {}
    pin = (data.get('biometric_pin') or '').strip()
    if pin and Employee.query.filter(Employee.biometric_pin == pin, Employee.id != emp.id).first():
        return fail('هذا الرقم مرتبط بموظف آخر')
    emp.biometric_pin = pin or None
    db.session.commit()
    return ok({'employee_id': emp.id, 'biometric_pin': emp.biometric_pin or ''}, 'تم حفظ رقم البصمة')


# ==================== الإعدادات ====================

@biometric_bp.route('/settings', methods=['GET'])
@login_required
def settings_get():
    bio.init_default_biometric_settings()
    rows = BiometricSetting.query.order_by(BiometricSetting.id).all()
    return ok([r.to_dict() for r in rows])


@biometric_bp.route('/settings', methods=['PUT'])
@login_required
def settings_update():
    if not _is_admin():
        return fail('غير مصرح لك بتعديل الإعدادات', 403)
    data = request.get_json(force=True, silent=True) or {}
    updated = []
    for key, value in (data.get('settings') or {}).items():
        bio.set_setting(key, value)
        updated.append(key)
    rows = BiometricSetting.query.order_by(BiometricSetting.id).all()
    return ok([r.to_dict() for r in rows], 'تم حفظ الإعدادات')


# ==================== الحالة ====================

@biometric_bp.route('/status', methods=['GET'])
@login_required
def status():
    bio.init_default_biometric_settings()
    return ok(bio.status_summary())


# ==================== استيراد ملف (CSV / Excel) ====================

def _rows_from_file(filename, content):
    """قراءة الصفوف من ملف CSV أو Excel"""
    name = (filename or '').lower()
    if name.endswith(('.xlsx', '.xlsm', '.xls')):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        rows = [[c for c in row] for row in ws.iter_rows(values_only=True)]
    else:
        import csv
        text = content.decode('utf-8-sig', errors='ignore')
        try:
            dialect = csv.Sniffer().sniff(text[:2000], delimiters=',;\t')
        except Exception:
            dialect = csv.excel
        rows = [r for r in csv.reader(io.StringIO(text), dialect)]
    return [[('' if c is None else c) for c in row] for row in rows]


@biometric_bp.route('/import', methods=['POST'])
@login_required
def import_file():
    """استيراد سجلات بصمة من ملف CSV/Excel"""
    if 'file' not in request.files:
        return fail('لم يتم إرسال ملف')
    f = request.files['file']
    if not f or not f.filename:
        return fail('لم يتم إرسال ملف')
    content = f.read()
    if not content:
        return fail('الملف فارغ')

    try:
        rows = _rows_from_file(f.filename, content)
    except Exception as e:
        return fail(f'تعذر قراءة الملف: {e}')

    if not rows:
        return fail('الملف لا يحتوي على بيانات')

    header = [str(h).strip().lower() for h in rows[0]]
    data_rows = rows[1:]

    def norm(text):
        """تطبيع اسم العمود: حروف صغيرة بدون مسافات وشرطات"""
        t = str(text or '').strip().lower()
        for ch in (' ', '_', '-', '.', ':', '(', ')', '[', ']', '/'):
            t = t.replace(ch, '')
        return t

    ALIASES = {
        'pin': ['pin', 'userid', 'user', 'employeeid', 'employeecode', 'code', 'empcode',
                'cardno', 'cardnumber', 'card', 'badgeno', 'badgenumber', 'staffno', 'staffid',
                'useridno', 'uid', 'رقم', 'كود', 'موظف', 'الموظف', 'رقمالبطاقة', 'رقمالبصمة'],
        'date': ['date', 'day', 'تاريخ', 'التاريخ', 'اليوم', 'attdate', 'workdate', 'punchdate'],
        'in': ['timein', 'checkin', 'checkintime', 'in', 'in time', 'intime', 'login', 'signin',
               'arrival', 'entry', 'دخول', 'وقتالدخول', 'الحضور', 'تسجيلالدخول'],
        'out': ['timeout', 'checkout', 'checkintime', 'out', 'outtime', 'logout', 'signout',
                'departure', 'exit', 'خروج', 'وقتالخروج', 'تسجيلالخروج'],
        'status': ['status', 'الحالة', 'حالة'],
    }

    norm_header = [norm(h) for h in header]

    def find_col(kind):
        aliases = ALIASES.get(kind, [])
        # 1) تطابق تام
        for a in aliases:
            for i, h in enumerate(norm_header):
                if h == norm(a):
                    return i
        # 2) بداية العمود تطابق الاسم (مع استبعاد المطابقات القصيرة جداً)
        for a in aliases:
            for i, h in enumerate(norm_header):
                if len(a) >= 3 and h.startswith(norm(a)):
                    return i
        # 3) احتواء
        for a in aliases:
            for i, h in enumerate(norm_header):
                if len(a) >= 4 and norm(a) in h:
                    return i
        return None

    col_pin = find_col('pin')
    col_date = find_col('date')
    col_out = find_col('out')
    col_in = find_col('in')
    # عمود وقت عام (Time) يُستخدم كوقت دخول عند عدم وجود أعمدة دخول/خروج منفصلة
    if col_in is None:
        for i, h in enumerate(norm_header):
            if i == col_out:
                continue
            if h in ('time', 'وقت', 'الوقت', 'timelog', 'punchtime'):
                col_in = i
                break

    if col_pin is None or (col_date is None and col_in is None):
        return fail('الملف يجب أن يحتوي على عمود رقم الموظف/البصمة وعمود التاريخ')

    device_id = request.form.get('device_id')
    device = BiometricDevice.query.get(int(device_id)) if device_id else None
    if not device:
        device = BiometricDevice(
            name=request.form.get('device_name') or 'استيراد ملف',
            direction='pull',
        )
        db.session.add(device)
        db.session.commit()

    col_status = find_col('status')

    logs = []
    for row in data_rows:
        if not row or all(str(c).strip() == '' for c in row):
            continue
        pin = str(row[col_pin]).strip() if col_pin < len(row) else ''
        if not pin:
            continue
        date_val = row[col_date] if (col_date is not None and col_date < len(row)) else None
        in_val = row[col_in] if (col_in is not None and col_in < len(row)) else None
        out_val = row[col_out] if (col_out is not None and col_out < len(row)) else None
        status_txt = str(row[col_status]).strip().lower() if (col_status is not None and col_status < len(row)) else ''

        dt_in = bio.combine_date_time(date_val, in_val)
        if not dt_in and date_val is not None:
            dt_in = bio.parse_datetime(date_val)
        if not dt_in:
            continue

        log_type = 'in'
        if status_txt in ('out', 'checkout', 'check out', 'check-out', 'خروج', 'punchout'):
            log_type = 'out'
        elif status_txt in ('in', 'checkin', 'check in', 'check-in', 'دخول', 'punchin'):
            log_type = 'in'

        logs.append({'pin': pin, 'time': dt_in, 'type': log_type, 'mode': 'card', 'raw': str(row)})

        if out_val is not None and str(out_val).strip():
            dt_out = bio.combine_date_time(date_val, out_val)
            if dt_out and dt_out != dt_in:
                logs.append({'pin': pin, 'time': dt_out, 'type': 'out', 'mode': 'card', 'raw': str(row)})

    if not logs:
        return fail('لم يتم التعرف على أي سجل في الملف')

    added, duplicated, unmapped = bio.ingest_logs(device, logs, source='import')
    device.last_sync_at = datetime.utcnow()
    device.last_sync_count = added
    device.last_sync_message = f'استيراد {added} سجل'
    db.session.commit()
    return ok({
        'added': added,
        'duplicated': duplicated,
        'unmapped_pins': unmapped,
        'device_id': device.id,
    }, f'تم استيراد {added} سجل')
