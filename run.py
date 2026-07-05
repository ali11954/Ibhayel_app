import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
print("=" * 50)
print("  Server starting on http://127.0.0.1:4500")
print("  Username: admin")
print("  Password: admin123")
print("=" * 50)
app.run(debug=False, host='127.0.0.1', port=4500)
