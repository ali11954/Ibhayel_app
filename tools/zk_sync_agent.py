"""وكيل سحب سجلات البصمة من أجهزة ZKTeco (Windows / Python).

يعمل على جهاز المكتب المرتبط بنفس شبكة جهاز البصمة، ويقوم بـ:
1) الاتصال بالجهاز عبر TCP (zkprotocol / pyzk) وسحب سجلات الحضور.
2) إرسالها إلى خادم النظام عبر HTTP (JSON) أو محلياً عبر ملفات CSV.

الاستخدام:
    python zk_sync_agent.py --ip 192.168.1.201 --port 4370 --password 123 \
        --server https://your-site.onrender.com --api-key SECRET

أو بدون خادم (سحب فقط إلى ملفات CSV):
    python zk_sync_agent.py --ip 192.168.1.201 --out logs/

المتطلبات:
    pip install pyzk requests
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    requests = None


def log(msg):
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{stamp}] {msg}', flush=True)


# ==================== الاتصال بجهاز ZKTeco ====================

def fetch_logs(ip, port=4370, password='', timeout=10, force_udp=False):
    """سحب السجلات من الجهاز. يعيد قائمة سجلات نصية."""
    try:
        from pyzk import ZK
    except ImportError:
        raise RuntimeError(
            'مكتبة pyzk غير مثبتة. ثبّتها بالأمر: pip install pyzk\n'
            'أو استخدم البرنامج المرفق مع الجهاز (ZKTimeWeb) وتصدير CSV ثم استيراده من صفحة "أجهزة البصمة".'
        )

    zk = ZK(ip, port=port, timeout=timeout, password=password or '', force_udp=force_udp)
    if not zk.connect():
        raise RuntimeError(f'تعذر الاتصال بالجهاز {ip}:{port} - تحقق من IP والمنفذ وكلمة المرور')

    logs = []
    try:
        # المستخدمون (لمعرفة أسماء الموظفين)
        users = {}
        try:
            for u in zk.get_users():
                users[str(getattr(u, 'uid', ''))] = getattr(u, 'name', '') or ''
        except Exception:
            pass

        for att in zk.get_attendance():
            ts = getattr(att, 'timestamp', None)
            if not ts:
                continue
            uid = str(getattr(att, 'uid', '') or '')
            log_type = 'out' if getattr(att, 'log_type', None) == 1 else 'in'
            logs.append({
                'pin': uid,
                'time': ts.strftime('%Y-%m-%d %H:%M:%S'),
                'type': log_type,
                'mode': 'fp',
                'employee_name': users.get(uid, ''),
            })
    finally:
        zk.disconnect()

    return logs


# ==================== الإرسال للخادم ====================

def send_to_server(server, api_key, device, logs, timeout=30):
    """إرسال السجلات إلى خادم النظام"""
    if not requests:
        raise RuntimeError('مكتبة requests غير مثبتة: pip install requests')
    url = server.rstrip('/') + '/api/biometric/ingest'
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['X-API-Key'] = api_key
    payload = {
        'device': device,
        'logs': logs,
        'source': 'agent',
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f'فشل الإرسال ({resp.status_code}): {resp.text[:200]}')
    return resp.json()


# ==================== الحفظ كملفات CSV ====================

def save_csv(logs, out_dir, prefix='zk'):
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.join(out_dir, f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with open(name, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['PIN', 'Name', 'Date', 'Time', 'Type'])
        for l in logs:
            dt = datetime.strptime(l['time'], '%Y-%m-%d %H:%M:%S')
            w.writerow([l['pin'], l.get('employee_name', ''), dt.strftime('%Y-%m-%d'),
                        dt.strftime('%H:%M:%S'), l['type']])
    return name


# ==================== الوضع التلقائي (خدمة) ====================

def run_loop(args, logs_state):
    log(f'بدء المزامنة كل {args.interval} دقيقة مع {args.ip}:{args.port}')
    while True:
        try:
            logs = fetch_logs(args.ip, args.port, args.password, args.timeout, args.udp)
            known = logs_state['seen']
            new = [l for l in logs if l['time'] not in known]
            for l in new:
                known.add(l['time'])
            log(f'جلب {len(logs)} سجل - جديد {len(new)}')
            if new:
                if args.server:
                    res = send_to_server(args.server, args.api_key, {
                        'name': args.device_name,
                        'serial_number': args.serial,
                    }, new)
                    log(f'تم الإرسال: {res.get("message") or res.get("data")}')
                if args.out:
                    path = save_csv(new, args.out, args.serial or 'zk')
                    log(f'تم الحفظ في {path}')
        except Exception as e:
            log(f'خطأ: {e}')
        time.sleep(max(60, args.interval * 60))


def main():
    p = argparse.ArgumentParser(description='وكيل مزامنة أجهزة البصمة ZKTeco')
    p.add_argument('--ip', required=True, help='عنوان IP للجهاز')
    p.add_argument('--port', type=int, default=4370, help='منفذ الاتصال (4370 افتراضي)')
    p.add_argument('--password', default='', help='كلمة مرور الاتصال بالجهاز')
    p.add_argument('--timeout', type=int, default=10)
    p.add_argument('--udp', action='store_true', help='استخدام UDP بدلاً من TCP')
    p.add_argument('--server', default=os.environ.get('ZK_SERVER', ''), help='عنوان الموقع لإرسال السجلات')
    p.add_argument('--api-key', default=os.environ.get('ZK_API_KEY', ''), help='مفتاح الاستقبال')
    p.add_argument('--device-name', default='جهاز البصمة', help='اسم الجهاز في النظام')
    p.add_argument('--serial', default='', help='الرقم التسلسلي للجهاز (SN)')
    p.add_argument('--out', default='', help='مجلد حفظ ملفات CSV')
    p.add_argument('--interval', type=int, default=5, help='الدقائق بين كل مزامنة (الوضع التلقائي)')
    p.add_argument('--loop', action='store_true', help='تشغيل الخدمة بشكل مستمر')
    p.add_argument('--once', action='store_true', help='سحب مرة واحدة فقط ثم الخروج')
    args = p.parse_args()

    if not args.loop and not args.once:
        args.once = True

    logs_state = {'seen': set()}

    if args.once:
        logs = fetch_logs(args.ip, args.port, args.password, args.timeout, args.udp)
        log(f'تم جلب {len(logs)} سجل')
        if args.server:
            res = send_to_server(args.server, args.api_key, {
                'name': args.device_name, 'serial_number': args.serial,
            }, logs)
            log(f'الإرسال: {res.get("message") or res.get("data")}')
        if args.out:
            path = save_csv(logs, args.out, args.serial or 'zk')
            log(f'تم الحفظ في {path}')
        if not args.server and not args.out:
            for l in logs[:20]:
                print(json.dumps(l, ensure_ascii=False))
            if len(logs) > 20:
                print(f'... و {len(logs) - 20} سجل آخر')
        return 0

    run_loop(args, logs_state)
    return 0


if __name__ == '__main__':
    sys.exit(main())
