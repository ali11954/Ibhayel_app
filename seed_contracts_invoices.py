# seed_contracts_invoices.py
from datetime import datetime, timedelta
import random
from models import db, Company, Contract, Invoice, Supplier, SupplierInvoice, ExpenseCategory


def seed_contracts_invoices():
    """إدخال بيانات تجريبية للعقود والفواتير والمصروفات"""

    print("=" * 60)
    print("📄 بدء إدخال بيانات العقود والفواتير والمصروفات...")
    print("=" * 60)

    # ==================== 1. الحصول على الشركات ====================
    companies = Company.query.all()
    if not companies:
        print("❌ لا توجد شركات في قاعدة البيانات. قم بتشغيل seed_database.py أولاً")
        return

    print(f"\n📌 1. الشركات المتاحة: {len(companies)}")

    # ==================== 2. إنشاء العقود ====================
    print("\n📌 2. إنشاء العقود...")

    contract_types = ['monthly', 'annual', 'quarterly']
    contract_statuses = ['active', 'completed', 'pending']

    contracts_data = [
        # عقود شركة السكر
        {'company_id': companies[0].id, 'contract_type': 'monthly', 'contract_value': 500000,
         'start_date': datetime(2026, 1, 1).date(), 'end_date': datetime(2026, 12, 31).date(),
         'notes': 'عقد صيانة وتشغيل'},
        {'company_id': companies[0].id, 'contract_type': 'annual', 'contract_value': 2000000,
         'start_date': datetime(2026, 1, 1).date(), 'end_date': datetime(2026, 12, 31).date(),
         'notes': 'عقد خدمات زراعية شاملة'},

        # عقود شركة سبأ
        {'company_id': companies[1].id, 'contract_type': 'monthly', 'contract_value': 350000,
         'start_date': datetime(2026, 2, 1).date(), 'end_date': datetime(2027, 1, 31).date(),
         'notes': 'عقد ري وتسميد'},
        {'company_id': companies[1].id, 'contract_type': 'quarterly', 'contract_value': 800000,
         'start_date': datetime(2026, 1, 15).date(), 'end_date': datetime(2026, 10, 15).date(),
         'notes': 'عقد مكافحة آفات'},

        # عقود مؤسسة هائل
        {'company_id': companies[2].id, 'contract_type': 'monthly', 'contract_value': 450000,
         'start_date': datetime(2026, 1, 1).date(), 'end_date': datetime(2026, 12, 31).date(),
         'notes': 'عقد تشغيل عمال'},
        {'company_id': companies[2].id, 'contract_type': 'annual', 'contract_value': 1500000,
         'start_date': datetime(2026, 3, 1).date(), 'end_date': datetime(2027, 2, 28).date(),
         'notes': 'عقد استشارات زراعية'},
    ]

    created_contracts = []
    for contract_data in contracts_data:
        existing = Contract.query.filter_by(
            company_id=contract_data['company_id'],
            contract_type=contract_data['contract_type'],
            start_date=contract_data['start_date']
        ).first()

        if not existing:
            contract = Contract(**contract_data)
            contract.remaining_amount = contract.contract_value
            contract.amount_received = 0
            contract.status = random.choice(contract_statuses)
            db.session.add(contract)
            db.session.flush()
            created_contracts.append(contract)
            print(f"   ✅ عقد: {contract.company.name} - {contract.contract_type} - {contract.contract_value:,.0f} ريال")
        else:
            print(f"   ⚠️ عقد موجود: {existing.company.name}")
            created_contracts.append(existing)

    db.session.commit()
    print(f"   📊 تم إنشاء {len(created_contracts)} عقد")

    # ==================== 3. إنشاء الفواتير للعقود ====================
    print("\n📌 3. إنشاء الفواتير للعقود...")

    invoice_statuses = ['paid', 'partial', 'pending']

    invoices_data = []
    invoice_count = 0

    for contract in created_contracts:
        # عدد الفواتير لكل عقد (1-4 فواتير)
        num_invoices = random.randint(1, 4)

        for i in range(num_invoices):
            # حساب مبلغ الفاتورة (نسبة من قيمة العقد)
            if contract.contract_type == 'monthly':
                invoice_amount = contract.contract_value
            elif contract.contract_type == 'quarterly':
                invoice_amount = contract.contract_value / 3
            else:  # annual
                invoice_amount = contract.contract_value / 12

            # مبلغ مدفوع (عشوائي)
            paid_percentage = random.choice([0, 0, 25, 50, 75, 100, 100])  # 0% أو 100% غالباً
            paid_amount = invoice_amount * paid_percentage / 100

            status = 'paid' if paid_amount >= invoice_amount else ('partial' if paid_amount > 0 else 'pending')

            # تاريخ الفاتورة (شهر عشوائي)
            month = random.randint(1, 3)  # يناير، فبراير، مارس
            day = random.randint(1, 25)
            invoice_date = datetime(2026, month, day).date()
            due_date = invoice_date + timedelta(days=random.randint(15, 45))

            invoice = Invoice(
                contract_id=contract.id,
                invoice_number=f"INV-{contract.company.name[:3]}-{month}{day}",
                amount=round(invoice_amount, 2),
                invoice_date=invoice_date,
                due_date=due_date,
                is_paid=(status == 'paid'),
                paid_amount=round(paid_amount, 2),
                payment_method=random.choice(['cash', 'bank_transfer', 'check']) if paid_amount > 0 else None,
                notes=f"فاتورة {i + 1} من {num_invoices} للعقد"
            )
            db.session.add(invoice)
            invoice_count += 1

            # تحديث العقد
            contract.amount_received += paid_amount
            contract.remaining_amount = contract.contract_value - contract.amount_received
            if contract.remaining_amount <= 0:
                contract.status = 'completed'
            elif contract.amount_received > 0:
                contract.status = 'active'

    db.session.commit()
    print(f"   ✅ تم إنشاء {invoice_count} فاتورة")

    # ==================== 4. إنشاء فئات المصروفات ====================
    print("\n📌 4. إنشاء فئات المصروفات...")

    expense_categories = [
        {'name': 'utilities', 'name_ar': 'كهرباء وماء', 'account_code': '530001'},
        {'name': 'rent', 'name_ar': 'إيجار', 'account_code': '530002'},
        {'name': 'office', 'name_ar': 'مستلزمات مكتبية', 'account_code': '530003'},
        {'name': 'equipment', 'name_ar': 'معدات وأدوات', 'account_code': '530004'},
        {'name': 'general', 'name_ar': 'مصروفات عامة', 'account_code': '530005'},
    ]

    categories_created = []
    for cat_data in expense_categories:
        existing = ExpenseCategory.query.filter_by(name=cat_data['name']).first()
        if not existing:
            category = ExpenseCategory(**cat_data)
            db.session.add(category)
            categories_created.append(category)
            print(f"   ✅ تم إضافة فئة: {cat_data['name_ar']}")
        else:
            print(f"   ⚠️ فئة موجودة: {cat_data['name_ar']}")
            categories_created.append(existing)

    db.session.commit()

    # ==================== 5. إنشاء الموردين ====================
    print("\n📌 5. إنشاء الموردين...")

    suppliers_data = [
        {'name': 'Electricity Corporation', 'name_ar': 'شركة الكهرباء', 'supplier_type': 'utility',
         'phone': '800123456', 'contact_person': 'أحمد محمود'},
        {'name': 'Water Authority', 'name_ar': 'هيئة المياه', 'supplier_type': 'utility', 'phone': '800234567',
         'contact_person': 'علي حسن'},
        {'name': 'Rent Office Co.', 'name_ar': 'مكتب الإيجار', 'supplier_type': 'rent', 'phone': '800345678',
         'contact_person': 'خالد عبدالله'},
        {'name': 'Office Supplies Ltd', 'name_ar': 'مستلزمات مكتبية', 'supplier_type': 'office', 'phone': '800456789',
         'contact_person': 'محمد سعيد'},
        {'name': 'Equipment Trading', 'name_ar': 'تجارة المعدات', 'supplier_type': 'equipment', 'phone': '800567890',
         'contact_person': 'ياسر أحمد'},
        {'name': 'General Services', 'name_ar': 'خدمات عامة', 'supplier_type': 'general', 'phone': '800678901',
         'contact_person': 'سامي علي'},
    ]

    created_suppliers = []
    for sup_data in suppliers_data:
        existing = Supplier.query.filter_by(name=sup_data['name']).first()
        if not existing:
            supplier = Supplier(**sup_data)
            db.session.add(supplier)
            created_suppliers.append(supplier)
            print(f"   ✅ تم إضافة مورد: {sup_data['name_ar']}")
        else:
            print(f"   ⚠️ مورد موجود: {sup_data['name_ar']}")
            created_suppliers.append(existing)

    db.session.commit()

    # ==================== 6. إنشاء فواتير الموردين ====================
    print("\n📌 6. إنشاء فواتير الموردين...")

    supplier_invoice_statuses = ['paid', 'partial', 'pending']
    supplier_invoice_count = 0

    for supplier in created_suppliers:
        # عدد الفواتير لكل مورد (2-4 فواتير)
        num_invoices = random.randint(2, 4)

        for i in range(num_invoices):
            # فئة عشوائية تتناسب مع نوع المورد
            if supplier.supplier_type == 'utility':
                category = ExpenseCategory.query.filter_by(name='utilities').first()
                amount = random.choice([5000, 7500, 10000, 12500, 15000])
            elif supplier.supplier_type == 'rent':
                category = ExpenseCategory.query.filter_by(name='rent').first()
                amount = random.choice([10000, 15000, 20000, 25000])
            elif supplier.supplier_type == 'office':
                category = ExpenseCategory.query.filter_by(name='office').first()
                amount = random.choice([2000, 3500, 5000, 7500])
            elif supplier.supplier_type == 'equipment':
                category = ExpenseCategory.query.filter_by(name='equipment').first()
                amount = random.choice([15000, 25000, 35000, 50000])
            else:
                category = ExpenseCategory.query.filter_by(name='general').first()
                amount = random.choice([3000, 5000, 8000, 10000])

            # نسبة الدفع
            paid_percentage = random.choice([0, 0, 50, 100, 100])
            paid_amount = amount * paid_percentage / 100

            status = 'paid' if paid_amount >= amount else ('partial' if paid_amount > 0 else 'pending')

            # تاريخ الفاتورة
            month = random.randint(1, 3)
            day = random.randint(1, 25)
            invoice_date = datetime(2026, month, day).date()
            due_date = invoice_date + timedelta(days=random.randint(15, 45))

            invoice = SupplierInvoice(
                invoice_number=f"SI-{supplier.name[:3]}-{month}{day}",
                supplier_id=supplier.id,
                category_id=category.id if category else None,
                amount=amount,
                invoice_date=invoice_date,
                due_date=due_date,
                paid_amount=paid_amount,
                remaining_amount=amount - paid_amount,
                status=status,
                description=f"فاتورة {supplier.name_ar} عن شهر {month}/2026",
                notes=f"فاتورة رقم {i + 1}"
            )
            db.session.add(invoice)
            supplier_invoice_count += 1

    db.session.commit()
    print(f"   ✅ تم إنشاء {supplier_invoice_count} فاتورة مورد")

    # ==================== 7. إحصائيات نهائية ====================
    print("\n" + "=" * 60)
    print("📊 إحصائيات البيانات المدخلة:")
    print("=" * 60)
    print(f"   📄 العقود: {len(created_contracts)}")
    print(f"   🧾 الفواتير الصادرة: {invoice_count}")
    print(f"   🏷️ فئات المصروفات: {len(categories_created)}")
    print(f"   🏢 الموردين: {len(created_suppliers)}")
    print(f"   📥 فواتير الموردين: {supplier_invoice_count}")
    print("=" * 60)

    # إجمالي المبالغ
    total_contracts_value = sum(c.contract_value for c in created_contracts)
    total_invoices_amount = sum(i.amount for i in Invoice.query.all())
    total_supplier_invoices = sum(i.amount for i in SupplierInvoice.query.all())

    print("\n💰 إجمالي المبالغ:")
    print(f"   قيمة العقود: {total_contracts_value:,.0f} ر.ي")
    print(f"   قيمة الفواتير الصادرة: {total_invoices_amount:,.0f} ر.ي")
    print(f"   قيمة فواتير الموردين: {total_supplier_invoices:,.0f} ر.ي")
    print("=" * 60)
    print("\n🎉 تم إدخال بيانات العقود والفواتير بنجاح!")


if __name__ == '__main__':
    from app import app

    with app.app_context():
        seed_contracts_invoices()