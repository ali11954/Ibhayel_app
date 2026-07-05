from flask import Blueprint, jsonify, request
from flask_login import login_required
from utils import role_required
from models import (
    Region, Location, EvaluationCriteria, Evaluation, Account, JournalEntry
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


def api_response(data=None, message='', success=True, status=200):
    return jsonify({'success': success, 'message': message, 'data': data}), status


@api_bp.route('/areas/<int:company_id>')
@login_required
def get_areas_by_company(company_id):
    areas = Region.query.filter_by(company_id=company_id).all()
    return jsonify({'success': True, 'data': [{'id': a.id, 'name': a.name} for a in areas]})


@api_bp.route('/locations/<int:area_id>')
@login_required
def get_locations_by_area(area_id):
    locations = Location.query.filter_by(region_id=area_id).all()
    return jsonify({'success': True, 'data': [{'id': l.id, 'name': l.name} for l in locations]})


@api_bp.route('/regions_by_company/<int:company_id>')
@login_required
def get_regions_by_company(company_id):
    try:
        regions = Region.query.filter_by(company_id=company_id).all()
        result = [{'id': r.id, 'name': r.name} for r in regions]
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_regions_by_company: {e}")
        return jsonify([])


@api_bp.route('/locations_by_region/<int:region_id>')
@login_required
def get_locations_by_region(region_id):
    try:
        locations = Location.query.filter_by(region_id=region_id).all()
        result = [{'id': l.id, 'name': l.name, 'address': l.address or ''} for l in locations]
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_locations_by_region: {e}")
        return jsonify([])


@api_bp.route('/criteria_by_location/<int:location_id>')
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


@api_bp.route('/evaluation-criteria/<int:id>')
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


@api_bp.route('/criteria-by-job-title')
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


@api_bp.route('/evaluation/<int:evaluation_id>')
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


@api_bp.route('/journal-entry/<int:entry_id>')
@login_required
def get_journal_entry_api(entry_id):
    entry = JournalEntry.query.get_or_404(entry_id)
    details = []
    for detail in entry.details:
        account = Account.query.get(detail.account_id)
        details.append({
            'account_code': account.code if account else '-',
            'account_name': f"{account.code} - {account.name_ar}" if account else '-',
            'debit': f"{detail.debit:,.2f}",
            'credit': f"{detail.credit:,.2f}"
        })
    return jsonify({
        'entry_number': entry.entry_number,
        'date': entry.date.strftime('%Y-%m-%d'),
        'description': entry.description,
        'details': details
    })
