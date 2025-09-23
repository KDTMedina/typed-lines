from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# Association tables for many-to-many relationships
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('date_followed', db.DateTime, default=datetime.utcnow)
)

blog_likes = db.Table('blog_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('blog_id', db.Integer, db.ForeignKey('blogs.id'), primary_key=True),
    db.Column('date_liked', db.DateTime, default=datetime.utcnow)
)

comment_likes = db.Table('comment_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('comment_id', db.Integer, db.ForeignKey('comments.id'), primary_key=True),
    db.Column('date_liked', db.DateTime, default=datetime.utcnow)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255), default='default.jpg')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    blogs = db.relationship('Blog', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    
    # Following relationships
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic'
    )
    
    # Likes relationships
    liked_blogs = db.relationship(
        'Blog', secondary=blog_likes,
        backref=db.backref('liked_by', lazy='dynamic'), lazy='dynamic'
    )
    
    liked_comments = db.relationship(
        'Comment', secondary=comment_likes,
        backref=db.backref('liked_by', lazy='dynamic'), lazy='dynamic'
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
    
    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
    
    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0
    
    def like_blog(self, blog):
        if not self.has_liked_blog(blog):
            self.liked_blogs.append(blog)
    
    def unlike_blog(self, blog):
        if self.has_liked_blog(blog):
            self.liked_blogs.remove(blog)
    
    def has_liked_blog(self, blog):
        return self.liked_blogs.filter(blog_likes.c.blog_id == blog.id).count() > 0
    
    def like_comment(self, comment):
        if not self.has_liked_comment(comment):
            self.liked_comments.append(comment)
    
    def unlike_comment(self, comment):
        if self.has_liked_comment(comment):
            self.liked_comments.remove(comment)
    
    def has_liked_comment(self, comment):
        return self.liked_comments.filter(comment_likes.c.comment_id == comment.id).count() > 0
    
    def __repr__(self):
        return f'<User {self.username}>'

class Blog(db.Model):
    __tablename__ = 'blogs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300))
    content = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(255))
    is_public = db.Column(db.Boolean, default=True, index=True)
    is_featured = db.Column(db.Boolean, default=False, index=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    date_updated = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationships
    comments = db.relationship('Comment', backref='blog', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def likes_count(self):
        return self.liked_by.count()
    
    @property
    def comments_count(self):
        return self.comments.count()
    
    def can_view(self, user):
        """Check if user can view this blog"""
        if self.is_public:
            return True
        if user and user.is_authenticated:
            # Author can always view their own blog
            if user.id == self.user_id:
                return True
            # Followers can view private blogs
            if user.is_following(self.author):
                return True
        return False
    
    def __repr__(self):
        return f'<Blog {self.title}>'

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    blog_id = db.Column(db.Integer, db.ForeignKey('blogs.id'), nullable=False, index=True)
    
    @property
    def likes_count(self):
        return self.liked_by.count()
    
    def __repr__(self):
        return f'<Comment {self.id}>'