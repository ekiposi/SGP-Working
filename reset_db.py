from app import app, db
from models import User
import os

def reset_db():
    with app.app_context():
        profiles_path = os.path.join('static', 'uploads', 'profiles')
        if os.path.exists(profiles_path):
            for imgs in os.listdir(profiles_path):
                if imgs.endswith('.jpg') or imgs.endswith('.jpeg') or imgs.endswith('.png'):
                    os.remove(os.path.join(profiles_path, imgs))
        
        qr_path = os.path.join('static', 'uploads', 'qrcodes')
        if os.path.exists(qr_path):
            for imgs in os.listdir(qr_path):
                if imgs.endswith('.jpg') or imgs.endswith('.jpeg') or imgs.endswith('.png'):
                    os.remove(os.path.join(qr_path, imgs))
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Create admin user
        admin = User(
            username='admin',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        
        print("Database reset successfully!")

if __name__ == '__main__':
    reset_db()
