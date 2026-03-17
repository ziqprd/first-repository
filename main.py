from flask import Flask, render_template, request, url_for, redirect
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
login_manager = LoginManager(app)

app.config['SECRET_KEY'] = 'abcd1234'
login_manager.login_view = 'login'

connection = sqlite3.connect('SQLite.db', check_same_thread=False)
cursor = connection.cursor()

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    user = cursor.execute(
        'SELECT id, username, password FROM user WHERE id = ?', (user_id,)).fetchone()
    if user is not None:
        return User(user[0], user[1], user[2])
    return None


def close_db(connection=None):
   if connection is not None:
       connection.close()
@app.teardown_appcontext
def close_connection(exception):
    close_db()


@app.route('/')
def index():
    cursor.execute('SELECT post.id, post.title, post.context, post.author_id, user.username, COUNT(like.id) AS likes FROM post JOIN user ON post.author_id = user.id LEFT JOIN like ON post.id = like.post_id GROUP BY post.id, post.title, post.context, post.author_id, user.username')
    result = cursor.fetchall()
    posts=[]
    for post in reversed(result):
        posts.append(
            {'id': post[0], 'title': post[1], 'context': post[2], 'author_id': post[3], 'username': post[4], 'likes': post[5]}
        )
        if current_user.is_authenticated:
            cursor.execute('SELECT post_id FROM like WHERE user_id = ?', (current_user.id,))
            likes_result = cursor.fetchall()
            liked_posts = []
            for like in likes_result:
                liked_posts.append(like[0])
            posts[-1]['liked_posts'] = liked_posts
    context = {'posts':posts}
    return render_template('blog.html', **context)


@app.route('/add/', methods=['GET', 'POST'])
@login_required
def addpost():
    if request.method == 'POST':
        title = request.form['title']
        context = request.form['context']
        cursor.execute(
            'INSERT INTO post(title, context, author_id) VALUES (?, ?, ?)',
            (title, context, current_user.id)
        )
        connection.commit()
        return redirect(url_for('index'))
    return render_template('add_post.html')


@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = cursor.execute('SELECT * FROM post WHERE id = ?', (post_id,)).fetchone()
    if post and post[3] == current_user.id:
        cursor.execute('DELETE FROM post WHERE id = ?', (post_id,))
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))




@app.route('/register/', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        try:
            cursor.execute(
                'INSERT INTO user(username, email, password) VALUES (?, ?, ?)',
                (username, email, generate_password_hash(password))
            )
            connection.commit()
            print('Регистрация прошла успешно')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', message='Username already exists!')
    return render_template('register.html')


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = cursor.execute(
            'SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        if user and User(user[0], user[1], user[2]).check_password(password):
            login_user(User(user[0], user[1], user[2]))
            return redirect(url_for('index'))
        else:
            return render_template('login.html', message='Invalid username or password!')
    return render_template('login.html')


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/post/<post_id>')
def post(post_id):
    result = cursor.execute(
        'SELECT * from post JOIN user ON post.author_id = user.id WHERE post.id = ?', (post_id,)).fetchone()
    post_dict = {'id': result[0], 'title': result[1], 'context': result[2], 'author_id': result[3], 'username': result[5]}
    all_comments = cursor.execute(
        'SELECT comments.text, user.username FROM comments JOIN user ON comments.author_id = user.id WHERE comments.post_id = ?', (post_id,)).fetchall()
    comments = []
    for comment in all_comments:
        comments.append({'text': comment[0], 'username': comment[1]})

    return render_template('post.html', post=post_dict, comments=comments)


def user_is_liking(user_id, post_id):
    like = cursor.execute("SELECT * FROM like WHERE user_id = ? AND post_id = ?",(user_id, post_id)).fetchone()
    return bool(like)


@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    post = cursor.execute('SELECT * FROM post WHERE id = ?',(post_id,)).fetchone()
    if post:
        if user_is_liking(current_user.id, post_id):
            cursor.execute('DELETE FROM like WHERE user_id = ? AND post_id = ?',(current_user.id, post_id))
            connection.commit()
            print('You unliked this post!')
        else:
            cursor.execute('INSERT INTO like (user_id, post_id) VALUES (?, ?)',(current_user.id, post_id))
            connection.commit()
            print('You liked this post!')
        return redirect(url_for('index'))
    return 'Post not found', 404

@app.route('/addcomment/<post_id>', methods=['GET', 'POST'])
@login_required
def comment_post(post_id):
    if request.method == 'POST':
        text = request.form['text']
        cursor.execute(
            'INSERT INTO comments(text, post_id, author_id) VALUES (?, ?, ?)',
            (text, post_id, current_user.id)
        )
        connection.commit()
        return redirect(url_for('post', post_id = post_id))
    else:
        return render_template('add_comment.html', post_id = post_id)



if __name__ ==  '__main__':
    app.run()