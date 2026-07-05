from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import (
    db, Employee, Evaluation, EvaluationCriteria,
    Company, Region, Location,
    AreaEvaluation, AreaEvaluationCriteria
)
from utils import role_required

evaluations_bp = Blueprint('evaluations', __name__)


@evaluations_bp.route('/evaluations')
@login_required
def evaluations_list():
    if current_user.role == 'admin':
        evaluations = Evaluation.query.order_by(Evaluation.date.desc()).all()
    elif current_user.role == 'supervisor':
        supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
        if supervisor_employee:
            workers = Employee.query.filter_by(company_id=supervisor_employee.company_id, is_active=True).all()
            worker_ids = [w.id for w in workers]
            evaluations = Evaluation.query.filter(Evaluation.employee_id.in_(worker_ids)).order_by(
                Evaluation.date.desc()).all()
        else:
            evaluations = []
    else:
        evaluations = []

    return render_template('evaluations/evaluations.html', evaluations=evaluations)


@evaluations_bp.route('/evaluations/add', methods=['GET', 'POST'])
@login_required
def add_evaluation():
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        region_id = request.form.get('region_id')
        location_id = request.form.get('location_id')
        comments = request.form.get('comments')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

        criteria_scores = []
        total_score = 0
        max_possible = 0

        for key, value in request.form.items():
            if key.startswith('criteria_'):
                criteria_id = int(key.split('_')[1])
                score = int(value)

                criteria = EvaluationCriteria.query.get(criteria_id)
                if criteria:
                    criteria_scores.append({
                        'criteria_id': criteria_id,
                        'name': criteria.name,
                        'score': score,
                        'max_score': criteria.max_score
                    })
                    total_score += score
                    max_possible += criteria.max_score

        percentage = (total_score / max_possible * 100) if max_possible > 0 else 0

        evaluation = Evaluation(
            employee_id=employee_id,
            evaluator_id=current_user.id,
            evaluation_type='supervisor',
            date=date,
            score=percentage,
            comments=comments,
            region_id=region_id if region_id else None,
            location_id=location_id if location_id else None
        )
        evaluation.set_criteria_scores(criteria_scores)
        db.session.add(evaluation)
        db.session.commit()

        flash('تم إضافة التقييم بنجاح', 'success')
        return redirect(url_for('evaluations.evaluations_list'))

    company_filter = None

    if current_user.role == 'admin':
        employees = Employee.query.filter(
            Employee.is_active == True,
            Employee.employee_type == 'worker'
        ).all()
        companies = Company.query.all()
    elif current_user.role == 'supervisor':
        supervisor_employee = Employee.query.filter_by(user_id=current_user.id).first()
        if supervisor_employee:
            company_filter = supervisor_employee.company_id
            employees = Employee.query.filter(
                Employee.is_active == True,
                Employee.employee_type == 'worker',
                Employee.company_id == company_filter
            ).all()
            companies = Company.query.filter_by(id=company_filter).all()
        else:
            employees = []
            companies = []
    else:
        employees = []
        companies = []

    employees_data = [{
        'id': e.id,
        'name': e.name,
        'job_title': e.job_title or 'عامل',
        'company_id': e.company_id,
        'employee_type': e.employee_type
    } for e in employees]

    regions = Region.query.all()
    regions_data = [{'id': r.id, 'name': r.name, 'company_id': r.company_id} for r in regions]

    locations = Location.query.all()
    locations_data = [{
        'id': l.id,
        'name': l.name,
        'region_id': l.region_id,
        'address': l.address or ''
    } for l in locations]

    job_titles = db.session.query(Employee.job_title).filter(
        Employee.job_title != None,
        Employee.job_title != ''
    ).distinct().all()
    job_titles = [j[0] for j in job_titles if j[0]]

    return render_template('evaluations/add_evaluation.html',
                           employees=employees_data,
                           companies=companies,
                           regions=regions_data,
                           locations=locations_data,
                           job_titles=job_titles,
                           company_filter=company_filter,
                           now=datetime.now())


@evaluations_bp.route('/api/regions_by_company/<int:company_id>')
@login_required
def get_regions_by_company(company_id):
    try:
        regions = Region.query.filter_by(company_id=company_id).all()
        result = [{'id': r.id, 'name': r.name} for r in regions]
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_regions_by_company: {e}")
        return jsonify([])


@evaluations_bp.route('/api/locations_by_region/<int:region_id>')
@login_required
def get_locations_by_region(region_id):
    try:
        locations = Location.query.filter_by(region_id=region_id).all()
        result = [{'id': l.id, 'name': l.name, 'address': l.address or ''} for l in locations]
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_locations_by_region: {e}")
        return jsonify([])


@evaluations_bp.route('/api/criteria_by_location/<int:location_id>')
@login_required
def get_criteria_by_location(location_id):
    try:
        criteria = EvaluationCriteria.query.filter_by(location_id=location_id, is_active=True).all()
        result = [{'id': c.id, 'name': c.name, 'description': c.description, 'max_score': c.max_score} for c in
                  criteria]
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f"Error in get_criteria_by_location: {e}")
        return jsonify({'success': False, 'data': []})


@evaluations_bp.route('/evaluation-criteria/add', methods=['GET'])
@login_required
@role_required('admin')
def add_evaluation_criteria_form():
    job_titles = db.session.query(Employee.job_title).filter(
        Employee.job_title != None,
        Employee.job_title != ''
    ).distinct().all()
    job_titles = [j[0] for j in job_titles if j[0]]

    return render_template('criteria/add.html', job_titles=job_titles)


@evaluations_bp.route('/evaluation-criteria/edit/<int:id>', methods=['GET'])
@login_required
@role_required('admin')
def edit_evaluation_criteria_form(id):
    criteria = EvaluationCriteria.query.get_or_404(id)

    job_titles = db.session.query(Employee.job_title).filter(
        Employee.job_title != None,
        Employee.job_title != ''
    ).distinct().all()
    job_titles = [j[0] for j in job_titles if j[0]]

    return render_template('criteria/edit.html',
                           criteria=criteria,
                           job_titles=job_titles)


@evaluations_bp.route('/evaluation-criteria')
@login_required
@role_required('admin')
def evaluation_criteria_list():
    criteria = EvaluationCriteria.query.filter_by(is_active=True).all()
    job_titles = db.session.query(Employee.job_title).filter(
        Employee.job_title != None,
        Employee.job_title != ''
    ).distinct().all()
    job_titles = [j[0] for j in job_titles if j[0]]

    return render_template('criteria/index.html',
                           criteria=criteria,
                           job_titles=job_titles)


@evaluations_bp.route('/evaluation-criteria/add', methods=['POST'])
@login_required
@role_required('admin')
def add_evaluation_criteria():
    try:
        job_title = request.form.get('job_title')
        name = request.form.get('name')
        description = request.form.get('description')
        min_score = int(request.form.get('min_score', 0))
        max_score = int(request.form.get('max_score', 10))

        if min_score >= max_score:
            flash('الحد الأدنى يجب أن يكون أقل من الحد الأقصى', 'danger')
            return redirect(url_for('evaluations.evaluation_criteria_list'))

        criteria = EvaluationCriteria(
            job_title=job_title,
            name=name,
            description=description,
            min_score=min_score,
            max_score=max_score
        )
        db.session.add(criteria)
        db.session.commit()
        flash(f'تم إضافة معيار "{name}" للوظيفة "{job_title}" بنجاح', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')

    return redirect(url_for('evaluations.evaluation_criteria_list'))


@evaluations_bp.route('/evaluation-criteria/edit/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def edit_evaluation_criteria(id):
    try:
        criteria = EvaluationCriteria.query.get_or_404(id)
        criteria.name = request.form.get('name')
        criteria.description = request.form.get('description')
        criteria.min_score = int(request.form.get('min_score', 0))
        criteria.max_score = int(request.form.get('max_score', 10))

        if criteria.min_score >= criteria.max_score:
            flash('الحد الأدنى يجب أن يكون أقل من الحد الأقصى', 'danger')
            return redirect(url_for('evaluations.evaluation_criteria_list'))

        db.session.commit()
        flash('تم تحديث معيار التقييم بنجاح', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')

    return redirect(url_for('evaluations.evaluation_criteria_list'))


@evaluations_bp.route('/evaluation-criteria/delete/<int:id>')
@login_required
@role_required('admin')
def delete_evaluation_criteria(id):
    try:
        criteria = EvaluationCriteria.query.get_or_404(id)
        criteria.is_active = False
        db.session.commit()
        flash('تم حذف معيار التقييم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ: {str(e)}', 'danger')

    return redirect(url_for('evaluations.evaluation_criteria_list'))


@evaluations_bp.route('/api/evaluation-criteria/<int:id>')
@login_required
@role_required('admin')
def get_evaluation_criteria_api(id):
    criteria = EvaluationCriteria.query.get_or_404(id)
    return jsonify({
        'success': True,
        'id': criteria.id,
        'job_title': criteria.job_title,
        'name': criteria.name,
        'description': criteria.description,
        'min_score': criteria.min_score,
        'max_score': criteria.max_score
    })


@evaluations_bp.route('/api/criteria-by-job-title')
@login_required
def get_criteria_by_job_title():
    job_title = request.args.get('job_title')
    if not job_title:
        return jsonify({'success': False, 'data': []})

    criteria = EvaluationCriteria.query.filter_by(
        job_title=job_title,
        is_active=True
    ).all()

    return jsonify({
        'success': True,
        'data': [{
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'min_score': c.min_score,
            'max_score': c.max_score
        } for c in criteria]
    })


@evaluations_bp.route('/evaluations/add_supervisor', methods=['GET', 'POST'])
@login_required
def add_supervisor_evaluation():
    if request.method == 'POST':
        criteria_scores = []
        for i in range(1, 8):
            score = request.form.get(f'criteria_{i}')
            if score:
                criteria_scores.append(int(score))

        total_score = sum(criteria_scores) if criteria_scores else 0

        evaluation = Evaluation(
            employee_id=request.form.get('employee_id'),
            evaluator_id=current_user.id,
            evaluation_type='contractor',
            score=total_score,
            comments=request.form.get('comments'),
            date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        )
        db.session.add(evaluation)
        db.session.commit()
        flash('تم إضافة تقييم المشرف بنجاح', 'success')
        return redirect(url_for('evaluations.evaluations_list'))

    employees = Employee.query.filter(
        Employee.is_active == True,
        Employee.job_title.contains('مشرف')
    ).all()
    return render_template('evaluations/add_supervisor_evaluation.html',
                           employees=employees,
                           now=datetime.now())


@evaluations_bp.route('/evaluations/areas')
@login_required
def area_evaluations_list():
    evaluations = AreaEvaluation.query.order_by(AreaEvaluation.evaluation_date.desc()).all()

    stats = {
        'total': len(evaluations),
        'regions': len([e for e in evaluations if e.evaluation_type == 'region']),
        'locations': len([e for e in evaluations if e.evaluation_type == 'location']),
        'avg_score': sum(e.overall_score for e in evaluations) / len(evaluations) if evaluations else 0,
        'pending': len([e for e in evaluations if e.status == 'pending']),
        'approved': len([e for e in evaluations if e.status == 'approved'])
    }

    return render_template('evaluations/area_evaluations.html',
                           evaluations=evaluations,
                           stats=stats,
                           now=datetime.now())


@evaluations_bp.route('/evaluations/areas/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'supervisor')
def add_area_evaluation():
    if request.method == 'POST':
        evaluation_type = request.form.get('evaluation_type')
        region_id = request.form.get('region_id')
        location_id = request.form.get('location_id')
        comments = request.form.get('comments', '')
        status = request.form.get('status', 'pending')

        criteria_scores = []
        total_score = 0
        max_possible = 0

        for key, value in request.form.items():
            if key.startswith('criteria_'):
                criteria_id = int(key.split('_')[1])
                score = int(value)

                criteria = AreaEvaluationCriteria.query.get(criteria_id)
                if criteria:
                    criteria_scores.append({
                        'criteria_id': criteria_id,
                        'name': criteria.name,
                        'score': score,
                        'max_score': criteria.max_score,
                        'weight': criteria.weight
                    })
                    total_score += score * criteria.weight
                    max_possible += criteria.max_score * criteria.weight

        overall_score = (total_score / max_possible * 10) if max_possible > 0 else 0

        evaluation = AreaEvaluation(
            evaluation_type=evaluation_type,
            region_id=region_id if evaluation_type == 'region' else None,
            location_id=location_id if evaluation_type == 'location' else None,
            evaluation_date=datetime.strptime(request.form.get('evaluation_date'), '%Y-%m-%d').date(),
            evaluator_id=current_user.id,
            overall_score=round(overall_score, 1),
            comments=comments,
            status=status
        )
        evaluation.set_criteria_scores(criteria_scores)
        db.session.add(evaluation)
        db.session.commit()

        flash('تم إضافة تقييم المنطقة/الموقع بنجاح', 'success')
        return redirect(url_for('evaluations.area_evaluations_list'))

    regions = Region.query.all()
    locations = Location.query.all()

    region_criteria = AreaEvaluationCriteria.query.filter_by(
        evaluation_type='region', is_active=True
    ).order_by(AreaEvaluationCriteria.order).all()

    location_criteria = AreaEvaluationCriteria.query.filter_by(
        evaluation_type='location', is_active=True
    ).order_by(AreaEvaluationCriteria.order).all()

    return render_template('evaluations/add_area_evaluation.html',
                           regions=regions,
                           locations=locations,
                           region_criteria=region_criteria,
                           location_criteria=location_criteria,
                           now=datetime.now())


@evaluations_bp.route('/evaluations/areas/view/<int:evaluation_id>')
@login_required
def view_area_evaluation(evaluation_id):
    evaluation = AreaEvaluation.query.get_or_404(evaluation_id)
    return render_template('evaluations/view_area_evaluation.html',
                           evaluation=evaluation,
                           now=datetime.now())


@evaluations_bp.route('/evaluations/areas/edit/<int:evaluation_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'supervisor')
def edit_area_evaluation(evaluation_id):
    evaluation = AreaEvaluation.query.get_or_404(evaluation_id)

    if request.method == 'POST':
        try:
            evaluation.comments = request.form.get('comments', '')
            evaluation.status = request.form.get('status', 'pending')

            criteria_scores = []
            total_score = 0
            max_possible = 0

            for key, value in request.form.items():
                if key.startswith('criteria_'):
                    criteria_id = int(key.split('_')[1])
                    score = int(value)

                    criteria = AreaEvaluationCriteria.query.get(criteria_id)
                    if criteria:
                        criteria_scores.append({
                            'criteria_id': criteria_id,
                            'name': criteria.name,
                            'score': score,
                            'max_score': criteria.max_score,
                            'weight': criteria.weight
                        })
                        total_score += score * criteria.weight
                        max_possible += criteria.max_score * criteria.weight

            evaluation.overall_score = (total_score / max_possible * 10) if max_possible > 0 else 0
            evaluation.set_criteria_scores(criteria_scores)
            db.session.commit()

            flash('تم تحديث التقييم بنجاح', 'success')
            return redirect(url_for('evaluations.area_evaluations_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    regions = Region.query.all()
    locations = Location.query.all()

    region_criteria = AreaEvaluationCriteria.query.filter_by(
        evaluation_type='region', is_active=True
    ).order_by(AreaEvaluationCriteria.order).all()

    location_criteria = AreaEvaluationCriteria.query.filter_by(
        evaluation_type='location', is_active=True
    ).order_by(AreaEvaluationCriteria.order).all()

    return render_template('evaluations/edit_area_evaluation.html',
                           evaluation=evaluation,
                           regions=regions,
                           locations=locations,
                           region_criteria=region_criteria,
                           location_criteria=location_criteria,
                           now=datetime.now())


@evaluations_bp.route('/evaluations/areas/delete/<int:evaluation_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_area_evaluation(evaluation_id):
    evaluation = AreaEvaluation.query.get_or_404(evaluation_id)

    try:
        db.session.delete(evaluation)
        db.session.commit()
        flash('تم حذف التقييم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء الحذف: {str(e)}', 'danger')

    return redirect(url_for('evaluations.area_evaluations_list'))


@evaluations_bp.route('/evaluations/areas/criteria', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def manage_area_criteria():
    if request.method == 'POST':
        evaluation_type = request.form.get('evaluation_type')
        name = request.form.get('name')
        description = request.form.get('description')
        weight = float(request.form.get('weight', 1))
        max_score = int(request.form.get('max_score', 10))
        order = int(request.form.get('order', 0))

        criteria = AreaEvaluationCriteria(
            evaluation_type=evaluation_type,
            name=name,
            description=description,
            weight=weight,
            max_score=max_score,
            order=order
        )
        db.session.add(criteria)
        db.session.commit()
        flash(f'تم إضافة معيار "{name}" بنجاح', 'success')
        return redirect(url_for('evaluations.manage_area_criteria'))

    region_criteria = AreaEvaluationCriteria.query.filter_by(
        evaluation_type='region'
    ).order_by(AreaEvaluationCriteria.order).all()

    location_criteria = AreaEvaluationCriteria.query.filter_by(
        evaluation_type='location'
    ).order_by(AreaEvaluationCriteria.order).all()

    return render_template('evaluations/area_criteria.html',
                           region_criteria=region_criteria,
                           location_criteria=location_criteria,
                           now=datetime.now())


@evaluations_bp.route('/evaluations/areas/criteria/delete/<int:criteria_id>', methods=['POST'])
@login_required
@role_required('admin')
def delete_area_criteria(criteria_id):
    criteria = AreaEvaluationCriteria.query.get_or_404(criteria_id)
    criteria.is_active = False
    db.session.commit()
    flash('تم حذف المعيار بنجاح', 'success')
    return redirect(url_for('evaluations.manage_area_criteria'))


@evaluations_bp.route('/api/evaluation/<int:evaluation_id>')
@login_required
def get_evaluation_details(evaluation_id):
    evaluation = Evaluation.query.get_or_404(evaluation_id)

    return jsonify({
        'success': True,
        'id': evaluation.id,
        'employee_name': evaluation.employee.name,
        'job_title': evaluation.employee.job_title,
        'region_name': evaluation.region.name if evaluation.region else None,
        'location_name': evaluation.location.name if evaluation.location else None,
        'date': evaluation.date.strftime('%Y-%m-%d'),
        'score': evaluation.score,
        'comments': evaluation.comments,
        'criteria_scores': evaluation.get_criteria_scores()
    })
