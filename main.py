from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import os
from smtplib import SMTP


my_email = os.environ.get('EMAIL')
passkey = os.environ.get('PASSKEY')
'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK-KEY')
ckeditor = CKEditor(app)
login_manager = LoginManager()
login_manager.init_app(app)

Bootstrap5(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if current_user.is_authenticated:
            if current_user.id == 1:
                return function(*args, **kwargs)
        else:
            abort(403)
    return wrapper_function

def send_email(email, name):
    text = """\
Welcome to Our Blog!

We're so glad you're here.

Dive into our latest posts, explore fresh perspectives, and join a community of curious minds.
Whether you're here to learn, get inspired, or just take a break, you're in the right place.

Happy reading,
Shahnewaz Hossain
            """
    try:
        with SMTP("smtp.gmail.com") as connection:
                connection.starttls()
                connection.login(user=my_email, password=passkey)
                connection.sendmail(
                    from_addr=my_email,
                    to_addrs=email,
                    msg=f"Subject:Blog WEB Response\n\nHey {name},\n{text}"
                )
    except:
        pass
# TODO: Configure Flask-Login


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", 'sqlite:///posts.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    author = relationship("User", back_populates='posts')
    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    comment_author = relationship("User", back_populates="comments")
    parent_post = relationship("BlogPost", back_populates="comments")

# TODO: Create a User table for all your registered users. 
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    posts = relationship("BlogPost", back_populates='author')
    comments = relationship("Comment", back_populates="comment_author")

with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET', 'POST'])
def register():
    user_form = RegisterForm()
    if user_form.validate_on_submit():
        email=user_form.email.data
        name=user_form.name.data
        new_user = User(
            email=email,
            password=generate_password_hash(user_form.password.data),
            name=name
        )
        try:
            db.session.add(new_user)
            db.session.commit()
        except:
            message = "You already have an account of that email. Login instead."
            return redirect(url_for('login', message=message))
        else:
            send_email(email, name)
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", form=user_form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = request.args.get('message')
    if message:
        flash(message)
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash("Password incorrect! Try again.")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=login_form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    print(f"This is my {id}.")
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment = Comment(
                text=form.comment.data,
                comment_author=current_user,
                post_id=post_id,
                parent_post=requested_post
            )
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))
        else:
            message = "You need to login first!"
            return redirect(url_for('login', message=message))
    comments = db.session.execute(db.select(Comment).where(post_id == post_id)).scalars().all()
    return render_template("post.html", post=requested_post, form=form, comments=comments)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            author_id = current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=['POST', 'GET'])
def contact():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        phone = request.form.get('phone')
        message = request.form.get('message')
        send_email(email, name)
        return redirect(url_for('get_all_posts'))
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
