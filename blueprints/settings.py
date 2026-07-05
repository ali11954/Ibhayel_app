from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Salary, SystemSettings, AllowanceSetting
from utils import role_required

settings_bp = Blueprint('settings_bp', __name__)


def allow_direct_journal_entry():
    if not current_user.is_authenticated:
        return False

    if current_user.role in ['admin', 'owner']:
        return True

    from models import Salary
    pending_salaries = Salary.query.filter_by(is_paid=False).count()
    if pending_salaries > 0:
        flash('⚠️ لا يمكن إنشاء قيود مباشرة قبل احتساب الرواتب', 'warning')
        return False

    return True


@settings_bp.route('/system/settings')
@login_required
@role_required('admin')
def system_settings_all():
    from models import SystemSettings, AllowanceSetting

    main_settings = SystemSettings.query.order_by(SystemSettings.display_order).all()
    allowances = AllowanceSetting.query.order_by(AllowanceSetting.display_order).all()

    return render_template('settings.html',
                           main_settings=main_settings,
                           allowances=allowances,
                           now=datetime.now())


@settings_bp.route('/system/settings/update', methods=['POST'])
@login_required
@role_required('admin')
def update_system_settings():
    from models import SystemSettings, AllowanceSetting, db

    print("\n" + "=" * 60)
    print("📋 البيانات المستلمة من النموذج:")
    for key, value in request.form.items():
        print(f"   {key}: {value}")
    print("=" * 60)

    try:
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                setting = SystemSettings.query.filter_by(setting_key=setting_key).first()
                if setting:
                    setting.value = float(value)
                    print(f"   ✅ تحديث الإعداد: {setting_key} = {value}")

        allowance_ids = request.form.getlist('allowance_ids[]')

        if not allowance_ids:
            allowance_ids = request.form.getlist('allowance_ids')

        print(f"\n📋 allowance_ids المستلمة: {allowance_ids}")

        for aid in allowance_ids:
            allowance = AllowanceSetting.query.get(int(aid))
            if allowance:
                value_key = f'allowance_value_{aid}'
                if value_key in request.form:
                    new_value = float(request.form.get(value_key, 0))
                    allowance.value = new_value
                    print(f"   ✅ {allowance.name_ar}: value = {new_value}")

                active_key = f'allowance_active_{aid}'
                allowance.is_active = active_key in request.form
                print(f"   ✅ {allowance.name_ar}: is_active = {allowance.is_active}")

                account_key = f'allowance_account_{aid}'
                if account_key in request.form:
                    account_code = request.form.get(account_key, '')
                    allowance.account_code = account_code if account_code else None
                    print(f"   ✅ {allowance.name_ar}: account_code = {account_code}")
                else:
                    print(f"   ⚠️ المفتاح {account_key} غير موجود في البيانات!")

        db.session.commit()
        flash('✅ تم تحديث إعدادات النظام بنجاح', 'success')

    except Exception as e:
        db.session.rollback()
        print(f"❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    return redirect(url_for('system_settings_all'))


@settings_bp.route('/system/settings/add-allowance', methods=['POST'])
@login_required
@role_required('admin')
def add_allowance():
    from models import AllowanceSetting, db

    try:
        allowance = AllowanceSetting(
            name=request.form.get('name'),
            name_ar=request.form.get('name_ar'),
            allowance_type=request.form.get('allowance_type'),
            value=float(request.form.get('value', 0)),
            based_on=request.form.get('based_on', 'basic_salary'),
            calculation_method=request.form.get('calculation_method', 'add'),
            applies_to=request.form.get('applies_to', 'all'),
            account_code=request.form.get('account_code'),
            description=request.form.get('description'),
            is_active=True
        )
        db.session.add(allowance)
        db.session.commit()
        flash(f'✅ تم إضافة البدل {allowance.name_ar} بنجاح', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    return redirect(url_for('system_settings_all'))


@settings_bp.route('/system/settings/edit-allowance/<int:allowance_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_allowance(allowance_id):
    from models import AllowanceSetting, db

    allowance = AllowanceSetting.query.get_or_404(allowance_id)

    if request.method == 'POST':
        try:
            allowance.name = request.form.get('name')
            allowance.name_ar = request.form.get('name_ar')
            allowance.allowance_type = request.form.get('allowance_type')
            allowance.value = float(request.form.get('value', 0))
            allowance.based_on = request.form.get('based_on', 'basic_salary')
            allowance.calculation_method = request.form.get('calculation_method', 'add')
            allowance.paid_to = request.form.get('paid_to', 'employee')
            allowance.applies_to = request.form.get('applies_to', 'all')
            allowance.account_code = request.form.get('account_code')
            allowance.description = request.form.get('description')
            allowance.is_active = request.form.get('is_active') == 'on'

            db.session.commit()
            flash(f'✅ تم تعديل البدل {allowance.name_ar} بنجاح', 'success')
            return redirect(url_for('system_settings_all'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ حدث خطأ: {str(e)}', 'danger')

    return render_template('edit_allowance.html', allowance=allowance, now=datetime.now())


@settings_bp.route('/system/settings/delete-allowance/<int:allowance_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_allowance(allowance_id):
    from models import AllowanceSetting, db

    allowance = AllowanceSetting.query.get_or_404(allowance_id)
    db.session.delete(allowance)
    db.session.commit()

    flash(f'✅ تم حذف البدل {allowance.name_ar} بنجاح', 'success')
    return redirect(url_for('system_settings'))
