from database.models import db, User, Quiz, Notification
from datetime import datetime
import os

def init_database(app):
    """Initialize database and create tables"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
        if not admin:
            admin = User(
                username=app.config['ADMIN_USERNAME'],
                is_admin=True
            )
            admin.set_password(app.config['ADMIN_PASSWORD'])  # Use password hashing
            db.session.add(admin)
        
        # Add sample notifications if none exist
        if Notification.query.count() == 0:
            notifications = [
                Notification(
                    title="Welcome to Offline Learning Hub!",
                    message="Start exploring resources and chat with our AI assistant.",
                    notification_type="success"
                ),
                Notification(
                    title="New Resources Available",
                    message="Check out the latest educational materials in the Resources section.",
                    notification_type="info"
                ),
                Notification(
                    title="Test Your Knowledge",
                    message="Try our interactive quizzes to assess your understanding.",
                    notification_type="info"
                )
            ]
            for notif in notifications:
                db.session.add(notif)
        
        # Add sample quiz if none exist
        if Quiz.query.count() == 0:
            sample_quiz = Quiz(
                title="Python Basics Quiz",
                description="Test your knowledge of Python programming fundamentals",
                category="Programming",
                difficulty="easy",
                questions=[
                    {
                        "id": 1,
                        "question": "What is the correct file extension for Python files?",
                        "options": [".python", ".py", ".pt", ".pyt"],
                        "correct_answer": 1
                    },
                    {
                        "id": 2,
                        "question": "Which keyword is used to define a function in Python?",
                        "options": ["function", "def", "func", "define"],
                        "correct_answer": 1
                    },
                    {
                        "id": 3,
                        "question": "What is the output of: print(2 ** 3)?",
                        "options": ["5", "6", "8", "9"],
                        "correct_answer": 2
                    },
                    {
                        "id": 4,
                        "question": "Which of these is a mutable data type in Python?",
                        "options": ["tuple", "string", "list", "integer"],
                        "correct_answer": 2
                    },
                    {
                        "id": 5,
                        "question": "What does 'len()' function do?",
                        "options": [
                            "Converts to length",
                            "Returns the length of an object",
                            "Creates a list",
                            "None of the above"
                        ],
                        "correct_answer": 1
                    }
                ]
            )
            db.session.add(sample_quiz)
        
        db.session.commit()
        print("✅ Database initialized successfully!")

def seed_sample_resources(app):
    """Add sample resources to database"""
    from database.models import Resource
    import os
    
    with app.app_context():
        if Resource.query.count() == 0:
            sample_dir = os.path.join(app.config['RESOURCES_PATH'], 'sample')
            
            # Define sample PDFs with actual file paths
            sample_files = [
                {
                    "filename": "Python_Programming_Basics.pdf",
                    "title": "Python Programming Basics",
                    "description": "Comprehensive introduction to Python programming covering variables, functions, control flow, and more",
                    "category": "Programming"
                },
                {
                    "filename": "Data_Structures_Guide.pdf",
                    "title": "Data Structures Guide",
                    "description": "Complete guide to data structures including arrays, lists, stacks, queues, trees, and hash tables",
                    "category": "Computer Science"
                },
                {
                    "filename": "Machine_Learning_Introduction.pdf",
                    "title": "Introduction to Machine Learning",
                    "description": "Learn the fundamentals of machine learning, supervised/unsupervised learning, and model evaluation",
                    "category": "AI & ML"
                }
            ]
            
            resources = []
            for file_info in sample_files:
                file_path = os.path.join(sample_dir, file_info['filename'])
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    resource = Resource(
                        title=file_info['title'],
                        filename=file_info['filename'],
                        file_path=file_path,
                        file_type="pdf",
                        file_size=file_size,
                        description=file_info['description'],
                        category=file_info['category'],
                        indexed=False
                    )
                    resources.append(resource)
                    db.session.add(resource)
            
            if resources:
                db.session.commit()
                print(f"✅ Added {len(resources)} sample resources!")
