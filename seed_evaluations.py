# seed_evaluations.py
from datetime import datetime, timedelta
import random
from models import db, Employee, Evaluation, AreaEvaluation, Region, Location, User, EvaluationCriteria, \
    AreaEvaluationCriteria


def seed_evaluations():
    """إدخال بيانات تقييمات تجريبية"""

    print("=" * 60)
    print("📊 بدء إدخال بيانات التقييمات التجريبية...")
    print("=" * 60)

    # ==================== 1. الحصول على المستخدم المدير ====================
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        print("❌ لم يتم العثور على المستخدم admin")
        return

    # ==================== 2. إنشاء معايير تقييم العمال (إذا لم تكن موجودة) ====================
    print("\n📌 1. إنشاء معايير تقييم العمال...")

    criteria_list = [
        {'job_title': 'عامل تسقية', 'name': 'جودة الري', 'description': 'دقة وفعالية عملية الري', 'min_score': 0,
         'max_score': 10},
        {'job_title': 'عامل تسقية', 'name': 'سرعة الإنجاز', 'description': 'سرعة إنجاز المهام المطلوبة', 'min_score': 0,
         'max_score': 10},
        {'job_title': 'عامل تسقية', 'name': 'الالتزام بالمواعيد', 'description': 'الحضور والانصراف في المواعيد المحددة',
         'min_score': 0, 'max_score': 10},
        {'job_title': 'عامل قص وتشكيل', 'name': 'جودة القص', 'description': 'دقة وجودة عملية القص والتشكيل',
         'min_score': 0, 'max_score': 10},
        {'job_title': 'عامل قص وتشكيل', 'name': 'الإنتاجية', 'description': 'كمية الإنتاج في الوقت المحدد',
         'min_score': 0, 'max_score': 10},
        {'job_title': 'مشرف', 'name': 'القيادة', 'description': 'قدرة على قيادة وإدارة الفريق', 'min_score': 0,
         'max_score': 10},
        {'job_title': 'مشرف', 'name': 'التنظيم', 'description': 'تنظيم العمل وتوزيع المهام', 'min_score': 0,
         'max_score': 10},
        {'job_title': 'مشرف', 'name': 'التواصل', 'description': 'التواصل مع الإدارة والعمال', 'min_score': 0,
         'max_score': 10},
    ]

    criteria_count = 0
    for crit in criteria_list:
        existing = EvaluationCriteria.query.filter_by(
            job_title=crit['job_title'],
            name=crit['name']
        ).first()
        if not existing:
            criteria = EvaluationCriteria(**crit)
            db.session.add(criteria)
            criteria_count += 1
            print(f"   ✅ تم إضافة معيار: {crit['job_title']} - {crit['name']}")
        else:
            print(f"   ⚠️ معيار موجود: {crit['job_title']} - {crit['name']}")

    db.session.commit()
    print(f"   📊 تم إضافة {criteria_count} معيار جديد")

    # ==================== 3. إنشاء معايير تقييم المناطق والمواقع ====================
    print("\n📌 2. إنشاء معايير تقييم المناطق والمواقع...")

    area_criteria_list = [
        # معايير المناطق
        {'evaluation_type': 'region', 'name': 'جودة التربة', 'name_ar': 'جودة التربة', 'weight': 2.0, 'max_score': 10,
         'order': 1},
        {'evaluation_type': 'region', 'name': 'توفر المياه', 'name_ar': 'توفر المياه', 'weight': 2.0, 'max_score': 10,
         'order': 2},
        {'evaluation_type': 'region', 'name': 'البنية التحتية', 'name_ar': 'البنية التحتية', 'weight': 1.5,
         'max_score': 10, 'order': 3},
        {'evaluation_type': 'region', 'name': 'الموقع الجغرافي', 'name_ar': 'الموقع الجغرافي', 'weight': 1.0,
         'max_score': 10, 'order': 4},
        {'evaluation_type': 'region', 'name': 'المناخ', 'name_ar': 'المناخ', 'weight': 1.5, 'max_score': 10,
         'order': 5},

        # معايير المواقع
        {'evaluation_type': 'location', 'name': 'نظافة الموقع', 'name_ar': 'نظافة الموقع', 'weight': 1.0,
         'max_score': 10, 'order': 1},
        {'evaluation_type': 'location', 'name': 'تنظيم العمل', 'name_ar': 'تنظيم العمل', 'weight': 1.5, 'max_score': 10,
         'order': 2},
        {'evaluation_type': 'location', 'name': 'جودة المحصول', 'name_ar': 'جودة المحصول', 'weight': 2.0,
         'max_score': 10, 'order': 3},
        {'evaluation_type': 'location', 'name': 'كفاءة الري', 'name_ar': 'كفاءة الري', 'weight': 1.5, 'max_score': 10,
         'order': 4},
        {'evaluation_type': 'location', 'name': 'صيانة المعدات', 'name_ar': 'صيانة المعدات', 'weight': 1.0,
         'max_score': 10, 'order': 5},
    ]

    area_criteria_count = 0
    for crit in area_criteria_list:
        existing = AreaEvaluationCriteria.query.filter_by(
            evaluation_type=crit['evaluation_type'],
            name=crit['name']
        ).first()
        if not existing:
            criteria = AreaEvaluationCriteria(**crit)
            db.session.add(criteria)
            area_criteria_count += 1
            print(f"   ✅ تم إضافة معيار: {crit['evaluation_type']} - {crit['name_ar']}")
        else:
            print(f"   ⚠️ معيار موجود: {crit['evaluation_type']} - {crit['name_ar']}")

    db.session.commit()
    print(f"   📊 تم إضافة {area_criteria_count} معيار جديد")

    # ==================== 4. إضافة تقييمات للعمال ====================
    print("\n📌 3. إضافة تقييمات للعمال...")

    employees = Employee.query.filter(Employee.employee_type == 'worker').all()
    evaluation_types = ['supervisor', 'contractor']
    evaluation_count = 0

    # تواريخ التقييم (آخر 3 أشهر)
    months = [
        {'month': 1, 'year': 2026, 'days': 31},
        {'month': 2, 'year': 2026, 'days': 28},
        {'month': 3, 'year': 2026, 'days': 31},
    ]

    for emp in employees:
        # لكل موظف 3-5 تقييمات
        for _ in range(random.randint(2, 4)):
            eval_type = random.choice(evaluation_types)
            eval_date = datetime(
                random.choice([2026, 2026, 2026, 2025]),
                random.randint(1, 12),
                random.randint(1, 28)
            ).date()

            # الحصول على معايير التقييم حسب الوظيفة
            criteria_list_db = EvaluationCriteria.query.filter_by(
                job_title=emp.job_title,
                is_active=True
            ).all()

            if not criteria_list_db:
                # إذا لم توجد معايير، استخدم معايير عامة
                criteria_list_db = EvaluationCriteria.query.filter_by(
                    job_title='عامل تسقية',
                    is_active=True
                ).all()

            if criteria_list_db:
                # حساب الدرجات
                criteria_scores = []
                total_score = 0
                max_possible = 0

                for crit in criteria_list_db:
                    score = random.randint(crit.min_score, crit.max_score)
                    criteria_scores.append({
                        'criteria_id': crit.id,
                        'name': crit.name,
                        'score': score,
                        'max_score': crit.max_score
                    })
                    total_score += score
                    max_possible += crit.max_score

                percentage = (total_score / max_possible * 10) if max_possible > 0 else 0

                evaluation = Evaluation(
                    employee_id=emp.id,
                    evaluator_id=admin_user.id,
                    evaluation_type=eval_type,
                    score=round(percentage, 1),
                    comments=f"تقييم {'دوري' if eval_type == 'supervisor' else 'نهائي'} - أداء {'ممتاز' if percentage >= 8 else 'جيد' if percentage >= 6 else 'مقبول'}",
                    date=eval_date
                )
                evaluation.set_criteria_scores(criteria_scores)
                db.session.add(evaluation)
                evaluation_count += 1

    db.session.commit()
    print(f"   ✅ تم إضافة {evaluation_count} تقييم للعمال")

    # ==================== 5. إضافة تقييمات للمناطق ====================
    print("\n📌 4. إضافة تقييمات للمناطق...")

    regions = Region.query.all()
    area_evaluation_count = 0

    for region in regions:
        # لكل منطقة 2-3 تقييمات
        for _ in range(random.randint(1, 3)):
            eval_date = datetime(2026, random.randint(1, 3), random.randint(1, 25)).date()

            # الحصول على معايير تقييم المناطق
            criteria_list_db = AreaEvaluationCriteria.query.filter_by(
                evaluation_type='region',
                is_active=True
            ).all()

            if criteria_list_db:
                criteria_scores = []
                total_score = 0
                max_possible = 0

                for crit in criteria_list_db:
                    score = random.randint(0, crit.max_score)
                    criteria_scores.append({
                        'criteria_id': crit.id,
                        'name': crit.name,
                        'score': score,
                        'max_score': crit.max_score,
                        'weight': crit.weight
                    })
                    total_score += score * crit.weight
                    max_possible += crit.max_score * crit.weight

                overall_score = (total_score / max_possible * 10) if max_possible > 0 else 0

                evaluation = AreaEvaluation(
                    evaluation_type='region',
                    region_id=region.id,
                    evaluation_date=eval_date,
                    evaluator_id=admin_user.id,
                    overall_score=round(overall_score, 1),
                    comments=f"تقييم منطقة {region.name} - {'جيد' if overall_score >= 7 else 'مقبول' if overall_score >= 5 else 'ضعيف'}",
                    status=random.choice(['pending', 'approved', 'rejected'])
                )
                evaluation.set_criteria_scores(criteria_scores)
                db.session.add(evaluation)
                area_evaluation_count += 1

    db.session.commit()
    print(f"   ✅ تم إضافة {area_evaluation_count} تقييم للمناطق")

    # ==================== 6. إضافة تقييمات للمواقع ====================
    print("\n📌 5. إضافة تقييمات للمواقع...")

    locations = Location.query.all()
    location_evaluation_count = 0

    for location in locations:
        # لكل موقع 2-3 تقييمات
        for _ in range(random.randint(1, 3)):
            eval_date = datetime(2026, random.randint(1, 3), random.randint(1, 25)).date()

            # الحصول على معايير تقييم المواقع
            criteria_list_db = AreaEvaluationCriteria.query.filter_by(
                evaluation_type='location',
                is_active=True
            ).all()

            if criteria_list_db:
                criteria_scores = []
                total_score = 0
                max_possible = 0

                for crit in criteria_list_db:
                    score = random.randint(0, crit.max_score)
                    criteria_scores.append({
                        'criteria_id': crit.id,
                        'name': crit.name,
                        'score': score,
                        'max_score': crit.max_score,
                        'weight': crit.weight
                    })
                    total_score += score * crit.weight
                    max_possible += crit.max_score * crit.weight

                overall_score = (total_score / max_possible * 10) if max_possible > 0 else 0

                evaluation = AreaEvaluation(
                    evaluation_type='location',
                    location_id=location.id,
                    evaluation_date=eval_date,
                    evaluator_id=admin_user.id,
                    overall_score=round(overall_score, 1),
                    comments=f"تقييم موقع {location.name} - {'ممتاز' if overall_score >= 8 else 'جيد' if overall_score >= 6 else 'مقبول'}",
                    status=random.choice(['pending', 'approved', 'rejected'])
                )
                evaluation.set_criteria_scores(criteria_scores)
                db.session.add(evaluation)
                location_evaluation_count += 1

    db.session.commit()
    print(f"   ✅ تم إضافة {location_evaluation_count} تقييم للمواقع")

    # ==================== 7. إحصائيات نهائية ====================
    print("\n" + "=" * 60)
    print("📊 إحصائيات التقييمات المدخلة:")
    print("=" * 60)
    print(f"   👥 معايير تقييم العمال: {criteria_count}")
    print(f"   🏢 معايير تقييم المناطق/المواقع: {area_criteria_count}")
    print(f"   📝 تقييمات العمال: {evaluation_count}")
    print(f"   🗺️ تقييمات المناطق: {area_evaluation_count}")
    print(f"   📍 تقييمات المواقع: {location_evaluation_count}")
    print("=" * 60)
    print("\n🎉 تم إدخال بيانات التقييمات التجريبية بنجاح!")


if __name__ == '__main__':
    from app import app

    with app.app_context():
        seed_evaluations()