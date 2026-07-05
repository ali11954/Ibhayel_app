from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from datetime import datetime
from models import db, Company, Region, Location, Employee, Contract, Invoice, EvaluationCriteria
from utils import role_required

companies_bp = Blueprint('companies', __name__, url_prefix='/companies')


@companies_bp.route('/')
@login_required
@role_required('admin')
def companies_dashboard():
    from sqlalchemy import func
    companies = Company.query.all()
    total_regions = 0
    total_locations = 0
    total_employees = 0
    for company in companies:
        total_regions += len(company.company_regions)
        total_employees += len(company.company_employees)
        for region in company.company_regions:
            total_locations += len(region.region_locations)
    stats = {
        'total_companies': len(companies),
        'total_regions': total_regions,
        'total_locations': total_locations,
        'total_employees': total_employees
    }
    companies_count = len(companies)
    active_contracts = Contract.query.filter_by(status='active').count()
    total_invoices_amount = db.session.query(func.sum(Invoice.amount)).scalar() or 0
    return render_template('companies/dashboard.html',
                           companies=companies,
                           stats=stats,
                           companies_count=companies_count,
                           active_contracts=active_contracts,
                           total_invoices_amount=f"{total_invoices_amount:,.0f}")


@companies_bp.route('/<int:company_id>')
@login_required
def company_details(company_id):
    company = Company.query.get_or_404(company_id)
    job_titles = db.session.query(Employee.job_title).filter(
        Employee.company_id == company_id,
        Employee.job_title != None,
        Employee.job_title != ''
    ).distinct().all()
    job_titles = [j[0] for j in job_titles if j[0]]
    evaluation_criteria = EvaluationCriteria.query.filter_by(
        company_id=company_id,
        is_active=True
    ).all()
    return render_template('companies/company_details.html',
                           company=company,
                           job_titles=job_titles,
                           evaluation_criteria=evaluation_criteria,
                           now=datetime.now())


@companies_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_company():
    if request.method == 'POST':
        existing = Company.query.filter_by(name=request.form.get('name')).first()
        if existing:
            flash('اسم الشركة موجود مسبقاً', 'danger')
            return redirect(url_for('companies.add_company'))
        company = Company(
            name=request.form.get('name'),
            contact_person=request.form.get('contact_person'),
            phone=request.form.get('phone'),
            email=request.form.get('email')
        )
        db.session.add(company)
        db.session.commit()
        flash('تم إضافة الشركة بنجاح', 'success')
        return redirect(url_for('companies.companies_dashboard'))
    return render_template('companies/add_company.html')


@companies_bp.route('/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_company(company_id):
    company = Company.query.get_or_404(company_id)
    if request.method == 'POST':
        company.name = request.form.get('name')
        company.contact_person = request.form.get('contact_person')
        company.phone = request.form.get('phone')
        company.email = request.form.get('email')
        db.session.commit()
        flash('تم تحديث بيانات الشركة بنجاح', 'success')
        return redirect(url_for('companies.company_details', company_id=company.id))
    return render_template('companies/edit_company.html', company=company)


@companies_bp.route('/<int:company_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    db.session.delete(company)
    db.session.commit()
    flash('تم حذف الشركة بنجاح', 'success')
    return redirect(url_for('companies.companies_dashboard'))


@companies_bp.route('/regions/add', methods=['POST'])
@login_required
@role_required('admin')
def add_region():
    company_id = request.form.get('company_id')
    region_name = request.form.get('region_name')
    existing = Region.query.filter_by(company_id=company_id, name=region_name).first()
    if existing:
        flash('هذه المنطقة موجودة مسبقاً لهذه الشركة', 'danger')
        return redirect(url_for('companies.company_details', company_id=company_id))
    region = Region(
        name=region_name,
        company_id=company_id
    )
    db.session.add(region)
    db.session.commit()
    flash('تم إضافة المنطقة بنجاح', 'success')
    return redirect(url_for('companies.company_details', company_id=company_id))


@companies_bp.route('/regions/<int:region_id>/edit', methods=['POST'])
@login_required
@role_required('admin')
def edit_region(region_id):
    region = Region.query.get_or_404(region_id)
    new_name = request.form.get('region_name')
    existing = Region.query.filter_by(company_id=region.company_id, name=new_name).first()
    if existing and existing.id != region_id:
        flash('هذا الاسم موجود مسبقاً لهذه الشركة', 'danger')
        return redirect(url_for('companies.company_details', company_id=region.company_id))
    region.name = new_name
    db.session.commit()
    flash('تم تحديث اسم المنطقة بنجاح', 'success')
    return redirect(url_for('companies.company_details', company_id=region.company_id))


@companies_bp.route('/regions/<int:region_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_region(region_id):
    region = Region.query.get_or_404(region_id)
    company_id = region.company_id
    db.session.delete(region)
    db.session.commit()
    flash('تم حذف المنطقة بنجاح', 'success')
    return redirect(url_for('companies.company_details', company_id=company_id))


@companies_bp.route('/locations/add', methods=['POST'])
@login_required
@role_required('admin')
def add_location():
    region_id = request.form.get('region_id')
    location_name = request.form.get('location_name')
    address = request.form.get('address')
    notes = request.form.get('notes')
    region = Region.query.get_or_404(region_id)
    existing = Location.query.filter_by(region_id=region_id, name=location_name).first()
    if existing:
        flash('هذا الموقع موجود مسبقاً لهذه المنطقة', 'danger')
        return redirect(url_for('companies.company_details', company_id=region.company_id))
    location = Location(
        name=location_name,
        region_id=region_id,
        address=address,
        notes=notes
    )
    db.session.add(location)
    db.session.commit()
    flash('تم إضافة الموقع بنجاح', 'success')
    return redirect(url_for('companies.company_details', company_id=region.company_id))


@companies_bp.route('/locations/<int:location_id>/edit', methods=['POST'])
@login_required
@role_required('admin')
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)
    location.name = request.form.get('location_name')
    location.address = request.form.get('address')
    location.notes = request.form.get('notes')
    db.session.commit()
    flash('تم تحديث بيانات الموقع بنجاح', 'success')
    return redirect(url_for('companies.company_details', company_id=location.region.company_id))


@companies_bp.route('/locations/<int:location_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    company_id = location.region.company_id
    db.session.delete(location)
    db.session.commit()
    flash('تم حذف الموقع بنجاح', 'success')
    return redirect(url_for('companies.company_details', company_id=company_id))
