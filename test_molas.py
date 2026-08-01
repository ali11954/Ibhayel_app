from app import app
from models import db, MolasCustomer, MolasOrder, MolasOrderItem, MolasPayment
from sqlalchemy import text

with app.app_context():
    result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'molas%'")).fetchall()
    print('Molas tables:', [r[0] for r in result])
    
    try:
        c = MolasCustomer(name='test', phone='123')
        db.session.add(c)
        db.session.commit()
        print('Customer created OK:', c.id)
        db.session.delete(c)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print('ERROR creating customer:', e)
