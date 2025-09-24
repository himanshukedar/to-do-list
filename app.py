from flask import Flask, render_template, request, redirect, url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# App Initialization
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'thisisasecretkey' # You should change this in a real application
db = SQLAlchemy(app)

# Login Manager Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Database Models ---
# --- Database Models --
task_tags = db.Table('task_tags',db.Column('task_id', db.Integer, db.ForeignKey('todo.id'), primary_key=True),db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True))
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    # User ab seedha tasks nahi, balki lists ka owner hai
    lists = db.relationship('TodoList', backref='owner', cascade="all, delete-orphan")

# NAYI TABLE: Har To-Do list ke liye
class TodoList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Har list ke andar tasks honge
    tasks = db.relationship('Todo', backref='list', cascade="all, delete-orphan")
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
# PURANI TABLE (Updated): Har task ab ek list se juda hai
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    # Ab user_id nahi, list_id hoga
    list_id = db.Column(db.Integer, db.ForeignKey('todo_list.id'), nullable=False)
    tags = db.relationship('Tag', secondary=task_tags, backref='tasks')
# --- Routes ---
# --- Routes ---

# Homepage ab lists dikhayega
@app.route('/')
@login_required
def home():
    lists = TodoList.query.filter_by(owner=current_user).all()
    return render_template('index.html', lists=lists)

# Naya route: Ek specific list ke tasks dikhane ke liye
@app.route('/list/<int:list_id>')
@login_required
def list_detail(list_id):
    list_item = TodoList.query.get_or_404(list_id)
    if list_item.owner != current_user:
        return 'Unauthorized', 403
    return render_template('list_detail.html', list_item=list_item)

# Naya route: Nayi list banane ke liye
@app.route('/add_list', methods=['POST'])
@login_required
def add_list():
    list_name = request.form.get('list_name')
    new_list = TodoList(name=list_name, owner=current_user)
    db.session.add(new_list)
    db.session.commit()
    flash('New list created!', 'success')
    return redirect(url_for('home'))

# Naya route: List ko delete karne ke liye
@app.route('/delete_list/<int:list_id>')
@login_required
def delete_list(list_id):
    list_to_delete = TodoList.query.get_or_404(list_id)
    if list_to_delete.owner != current_user:
        return 'Unauthorized', 403
    db.session.delete(list_to_delete)
    db.session.commit()
    flash('List deleted.', 'info')
    return redirect(url_for('home'))

# Task add karne ki logic (ab list_id ke saath)
@app.route('/list/<int:list_id>/add_task', methods=['POST'])
@login_required
def add_task(list_id):
    list_item = TodoList.query.get_or_404(list_id)
    if list_item.owner != current_user:
        return 'Unauthorized', 403
    task_content = request.form.get('task_name')
    new_task = Todo(content=task_content, list_id=list_item.id)
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for('list_detail', list_id=list_id))

# Task ko update aur delete karne ki logic (redirects badal gaye)
@app.route('/update_task/<int:task_id>')
@login_required
def update_task(task_id):
    task = Todo.query.get_or_404(task_id)
    if task.list.owner != current_user:
        return 'Unauthorized', 403
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for('list_detail', list_id=task.list_id))

@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Todo.query.get_or_404(task_id)
    list_id = task.list_id
    if task.list.owner != current_user:
        return 'Unauthorized', 403
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'info')
    return redirect(url_for('list_detail', list_id=list_id))

# Baki routes (login, register, logout) waise hi rahenge
# ... (Purane login, register, logout, edit_task routes yahan paste kar dein) ...
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            flash('Logged in successfully!','success')
            return redirect(url_for('home'))
        else :
            flash('login Unsuccessfully. Please check username and password','danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('you have been logged out','info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        new_user = User(username=request.form.get('username'), password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('account created successfully! you can now log in','success')
        return redirect(url_for('login'))
    return render_template('register.html')
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Todo.query.get_or_404(id)

    # Check if the task belongs to the current user
    if task.list.owner != current_user:
        return 'Unauthorized', 403

    if request.method == 'POST':
        task.content = request.form.get('content')
        try:
            db.session.commit()
            flash('Task updated successfully!', 'success')
            return redirect(url_for('home'))
        except:
            return 'There was an issue updating your task'
    else:
        return render_template('edit.html', task=task)
@app.route('/add_tag/<int:task_id>', methods=['POST'])
@login_required
def add_tag(task_id):
    task = Todo.query.get_or_404(task_id)
    if task.list.owner != current_user:
        return 'Unauthorized', 403

    tag_name = request.form.get('tag_name').strip().lower() # Tag ko clean karna
    if tag_name:
        # Check karein ki kya tag pehle se hai
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if existing_tag:
            # Agar hai, to use task se jod dein
            task.tags.append(existing_tag)
        else:
            # Agar nahi, to naya tag banakar jod dein
            new_tag = Tag(name=tag_name)
            task.tags.append(new_tag)
        
        db.session.commit()
        flash(f'Tag "{tag_name}" added!', 'success')
        
    return redirect(url_for('list_detail', list_id=task.list_id))

from app import app, db
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
