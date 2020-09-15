from flask import Flask, jsonify, request, json, make_response
from flask_mysqldb import MySQL
from datetime import datetime
from flask_cors import CORS
from flask_jwt_extended import (JWTManager, create_access_token)
from flask_bcrypt import Bcrypt
from datetime import datetime

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'reddit'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['JWT_SECRET_KEY'] = 't1NP63m4wnBg6nyHYKfmc2TpCOGI4nss'

mysql = MySQL(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)

# User Authorization


@app.route('/api/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        email = data['email']
        username = data['username']
        password = bcrypt.generate_password_hash(
            data['password']).decode('utf-8')
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM users WHERE email = '{0}'".format(email))
        rv = cur.fetchone()
        if rv:
            return jsonify(error_message="Email already exists")
        cur.execute(
            "SELECT * FROM users WHERE username = '{0}'".format(username))
        rv = cur.fetchone()
        if rv:
            return jsonify(error_message="Username already exists")

        cur.execute("INSERT INTO users(email, username, password) VALUES (%s, %s, %s)",
                    (email, username, password))
        mysql.connection.commit()
        cur.close()

        new_user = {
            'email': email,
            'username': username,
            'password': password
        }
        return jsonify(new_user=new_user)
    return


@app.route('/api/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data['username']
        password = data['password']
        result = ""
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username = '{0}'".format(username))
        rv = cur.fetchone()

        if not rv:
            return jsonify(error_message="Username does not exist.")
        else:
            if bcrypt.check_password_hash(rv['password'], password):
                access_token = create_access_token(
                    identity={'username': rv['username']})
                result = jsonify(access_token=access_token, username=username)
            else:
                result = jsonify(error_message="Wrong Password")
            return result
    return


@app.route('/api/submit', methods=['GET', 'POST'])
def post_submit():
    if request.method == 'POST':
        data = request.get_json()
        title = data['title']
        content = data['content']
        username = data['username']
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id FROM users WHERE username = '{0}' LIMIT 1".format(username))
        authorID = cur.fetchone()['id']
        cur.execute("INSERT INTO posts(authorID, username, title, content, createdAt) VALUES (%s, %s, %s, %s, %s)", (
            authorID, username, title, content, datetime.now()))
        mysql.connection.commit()
        cur.close()
        return make_response(jsonify(message="Post Submitted"), 200)
    return

# POST


@app.route('/api/posts')
def get_posts():
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT postID, username, title, content, num_of_comments, createdAt, upVote FROM posts ORDER BY postID desc")
    posts = cur.fetchall()
    return jsonify(post_arr=posts)


@app.route('/api/posts/upvote', methods=['GET', 'PATCH'])
def upvote_post():
    if request.method == 'PATCH':
        data = request.get_json()
        postID = data['postID']
        isUpVote = data['isUpVote']
        cur = mysql.connection.cursor()
        if isUpVote:
            cur.execute(
                "UPDATE posts SET upVote = upVote + 1 WHERE postID = '{0}'".format(postID))
            mysql.connection.commit()
        else:
            cur.execute(
                "UPDATE posts SET upVote = upVote - 1 WHERE postID = '{0}'".format(postID))
            mysql.connection.commit()
        return make_response(jsonify(message="Vote for post updated"), 200)
    return


@app.route('/api/post', methods=['GET'])
def get_post():
    postID = request.args.get('postID')
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT username, title, content, num_of_comments, createdAt, upVote FROM posts WHERE postID = '{0}'".format(int(postID)))
    post = cur.fetchone()
    return jsonify(post=post)

# Comment


@app.route('/api/post_comment', methods=['GET', 'POST'])
def post_comment():
    if request.method == 'POST':
        data = request.get_json()
        username = data['username']
        postID = data['postID']
        content = data['content']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO comments(postID, username, createdAt, content) VALUES (%s, %s, %s, %s)",
                    (postID, username, datetime.now(), content))
        cur.execute(
            "UPDATE posts SET num_of_comments = num_of_comments + 1 WHERE postID = '{0}'".format(postID))
        mysql.connection.commit()
        return make_response(jsonify(message="Comment Posted"), 200)
    return


@app.route('/api/get_comment')
def get_comment():
    postID = request.args.get('postID')
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT commentID, username, createdAt, content, points FROM comments WHERE parentID IS NULL and postID = '{0}'".format(postID))
    comments = cur.fetchall()
    cur.execute(
        "SELECT num_of_comments FROM posts WHERE postID = '{0}'".format(postID))
    numComments = cur.fetchone()
    return jsonify(comments=comments, numComments=numComments)


@app.route('/api/posts/upvote/comment', methods=['GET', 'PATCH'])
def upVote_comment():
    if request.method == 'PATCH':
        data = request.get_json()
        commentID = data['commentID']
        isUpVote = data['isUpVote']
        cur = mysql.connection.cursor()
        if isUpVote:
            cur.execute(
                "UPDATE comments SET points = points + 1 WHERE commentID = '{0}'".format(commentID))
            mysql.connection.commit()
        else:
            cur.execute(
                "UPDATE comments SET points = points - 1 WHERE commentID = '{0}'".format(commentID))
            mysql.connection.commit()
        return make_response(jsonify(message="Vote for post updated"), 200)
    return


@app.route('/api/post_reply', methods=['GET', 'POST'])
def post_reply():
    if request.method == 'POST':
        data = request.get_json()
        parentID = data['parentID']
        username = data['username']
        content = data['content']
        postID = data['postID']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO comments(parentID, username, content, postID, createdAt) VALUES (%s, %s, %s, %s, %s)",
                    (parentID, username, content, postID, datetime.now()))
        mysql.connection.commit()
        cur.execute(
            "UPDATE posts SET num_of_comments = num_of_comments + 1 WHERE postID = '{0}'".format(postID))
        mysql.connection.commit()
        return make_response(jsonify(message="Reply Posted"), 200)
    return


@app.route('/api/get_reply', methods=['GET'])
def get_reply():
    commentID = request.args.get('commentID')
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT commentID, username, createdAt, content, points FROM comments WHERE parentID = '{0}'".format(commentID))
    replies = cur.fetchall()
    return jsonify(replies=replies)
