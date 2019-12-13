from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug import secure_filename
import json
import os
import math
from datetime import datetime


with open('config.json', 'r') as c:
    params = json.load(c)["params"]

app = Flask(__name__)


app.secret_key = 'dont-tell-anyone'
app.config['UPLOAD_FOLDER'] = params['upload_location']
ALLOWED_EXTENSIONS = set(['jpg', 'jpeg'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


local_server = True
if(local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']


db = SQLAlchemy(app)



class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)



class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(40), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)
    countcomm=db.Column(db.Integer, default=0)
    views=db.Column(db.Integer, default=0)



class Comments(db.Model):
    cid = db.Column(db.Integer, primary_key=True)
    postid = db.Column(db.Integer, db.ForeignKey('posts.sno'), nullable=False) 
    commentdate = db.Column(db.DateTime, nullable=True, default=datetime.now) 
    name = db.Column(db.String(50), nullable=False, unique=True)
    emailid = db.Column(db.String(65), nullable=False, unique=False)
    message = db.Column(db.String(550), nullable=False)


@app.route("/")
def home():
    posts = Posts.query.filter_by().order_by(Posts.sno.desc()).all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))
    page = request.args.get('page')
    
    if(not str(page).isnumeric()):
        page = 1
    
    page= int(page)
    posts = posts[(page-1)*int(params['no_of_posts']): 
                  (page-1)*int(params['no_of_posts'])+ int(params['no_of_posts'])]
    
    if (page==1):
        prev = "/?page="+ str(page+1)
        next = "#"
    elif(page==last):
        prev = "#"
        next = "/?page=" + str(page - 1)
    else:
        prev = "/?page=" + str(page + 1)
        next = "/?page=" + str(page - 1)
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route("/post/<string:post_slug>", methods=['GET','POST'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    cocomment=Comments.query.filter_by(postid=post.sno).all()
    post.views += 1
    db.session.commit()

    if request.method == 'POST':
        name=request.form.get('name')
        emailid=request.form.get('emailid')
        message=request.form.get('message')
        comments=Comments(name=name, emailid=emailid, message=message, postid=post.sno)
        db.session.add(comments)
        post.countcomm += 1
        db.session.commit()    
    return render_template('posts.html', params=params, post=post, cocomment=cocomment)


# @app.route("/search", methods=['GET','POST'])
# def search():
#     # still in developement phase.
#     return render_template('index.html', params=params, post=post)



@app.route("/about")
def about():
    return render_template('about.html', params=params)



@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if ('user' in session and session['user'] == params['admin_user']):
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts = posts)
    
    if request.method=='POST':
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        
        if (username == params['admin_user'] and userpass == params['admin_password']):
            #set the session variable
            session['user'] = username
            posts = Posts.query.all()
            flash("LogIn Successful")
            return render_template('dashboard.html', params=params, posts = posts)

    return render_template('login.html', params=params)



@app.route("/edit/<string:sno>", methods = ['GET', 'POST'])
def edit(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == 'POST':
            box_title = request.form.get('title')
            postedby = request.form.get('postedby')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            if sno=='0':
                post = Posts(title=box_title, slug=slug, content=content, author=postedby, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.slug = slug
                post.content = content
                post.author = postedby
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/'+sno)

        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)



@app.route("/uploader", methods = ['GET', 'POST'])
def uploader():
    if ('user' in session and session['user'] == params['admin_user']):
        if (request.method == 'POST'):
            f= request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename) ))
            return redirect('/')
        else:
            return redirect('/dashboard')

    return redirect('/dashboard')



@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')



@app.route("/delete/<string:sno>", methods = ['GET', 'POST'])
def delete(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')



@app.route("/contact", methods = ['GET', 'POST'])
def contact():
    if(request.method=='POST'):
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, phone_num = phone, msg = message, date= datetime.now(),email = email )
        db.session.add(entry)
        db.session.commit()
        flash('Contact Submitted Successfully')
    return render_template('contact.html', params=params)



app.run(debug=True)