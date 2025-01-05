import unittest
from app import app, db
from models import User, Employee, Attendance
from datetime import datetime, timedelta
import json
import os

class TestReportSystem(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_attendance.db'
        self.client = app.test_client()
        
        # Remove test database if it exists
        if os.path.exists('test_attendance.db'):
            os.remove('test_attendance.db')
        
        with app.app_context():
            db.create_all()
            
            # Create test admin user
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', is_admin=True)
                admin.set_password('admin123')
                db.session.add(admin)
            
            # Create test employees
            departments = ['Administration et Direction', 'Personnel Médical', 'Personnel Paramédical']
            positions = ['Comptable', 'Médecin généraliste', 'Infirmier(ère) [soins généraux]']
            
            for i in range(3):
                emp = Employee(
                    pluri_id=f'EMP{i+1}',
                    first_name=f'Test{i+1}',
                    last_name=f'Employee{i+1}',
                    email=f'emp{i+1}@test.com',
                    phone=f'+123456789{i}',
                    department=departments[i],
                    position=positions[i],
                    hire_date=datetime.now().date()
                )
                db.session.add(emp)
            
            db.session.commit()
            
            # Create test attendance records
            employees = Employee.query.all()
            today = datetime.now()
            
            for emp in employees:
                for days_ago in range(3):
                    date = today - timedelta(days=days_ago)
                    check_in = date.replace(hour=9, minute=0, second=0)
                    check_out = date.replace(hour=17, minute=0, second=0)
                    
                    attendance = Attendance(
                        employee_id=emp.id,
                        date=date.date(),
                        check_in=check_in,
                        check_out=check_out
                    )
                    db.session.add(attendance)
            
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        # Remove test database
        if os.path.exists('test_attendance.db'):
            os.remove('test_attendance.db')

    def login(self):
        return self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

    def test_report_page_access(self):
        # Test unauthorized access
        response = self.client.get('/report')
        self.assertEqual(response.status_code, 302)  # Should redirect to login
        
        # Test authorized access
        self.login()
        response = self.client.get('/report')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reports', response.data)

    def test_report_data_api(self):
        self.login()
        
        # Test without filters
        response = self.client.get('/api/report_data')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('data', data)
        self.assertEqual(len(data['data']), 9)  # 3 employees * 3 days
        
        # Test with department filter
        response = self.client.get('/api/report_data?department=Personnel+M%C3%A9dical')
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 3)  # 1 employee * 3 days
        
        # Test with employee name filter
        response = self.client.get('/api/report_data?employee_name=Employee1')
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 3)  # 1 employee * 3 days
        
        # Test with date filter
        today = datetime.now().strftime('%Y-%m-%d')
        response = self.client.get(f'/api/report_data?date_from={today}&date_to={today}')
        data = json.loads(response.data)
        self.assertEqual(len(data['data']), 3)  # 3 employees * 1 day

    def test_report_data_format(self):
        self.login()
        response = self.client.get('/api/report_data')
        data = json.loads(response.data)
        
        # Check first record format
        record = data['data'][0]
        required_fields = [
            'pluri_id', 'full_name', 'department', 'function',
            'date', 'check_in', 'check_out', 'total_hours'
        ]
        for field in required_fields:
            self.assertIn(field, record)
        
        # Verify total hours calculation
        self.assertAlmostEqual(record['total_hours'], 8.0, places=1)  # 9 AM to 5 PM = 8 hours

if __name__ == '__main__':
    unittest.main()
