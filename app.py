from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
import os
import uuid
from pytz import timezone
from datetime import datetime
from config import Config
from models import db, User, Blog, Comment
from forms import (LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm,
                   ChangePasswordForm, EditProfileForm, BlogForm, CommentForm)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Utility functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_image(form_image, folder, size=(800, 600)):
    """Save uploaded image with compression and resizing"""
    random_hex = str(uuid.uuid4().hex)
    _, f_ext = os.path.splitext(form_image.filename)
    image_filename = random_hex + f_ext
    image_path = os.path.join(app.root_path, 'static/uploads', folder, image_filename)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    
    # Resize and compress image
    img = Image.open(form_image)
    img.thumbnail(size, Image.Resampling.LANCZOS)
    
    # Convert RGBA to RGB if necessary
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    img.save(image_path, quality=85, optimize=True)
    return image_filename

# Routes

@app.route('/')
def index():
    """Home page with featured blog and recent blogs"""
    # Get all featured blogs
    featured_blogs = Blog.query.filter_by(is_featured=True, is_public=True).order_by(Blog.date_created.desc()).all()
    
    # Get recent public blogs
    recent_blogs = Blog.query.filter_by(is_public=True).order_by(Blog.date_created.desc()).limit(6).all()

    print("Featured blog:", featured_blogs)
    print("Recent blogs:", recent_blogs)
    print("Users count:", User.query.count())
    print("Blogs count:", Blog.query.count())
    print("DB URI:", app.config['SQLALCHEMY_DATABASE_URI'])

    # If user is logged in, also include blogs from followed users
    if current_user.is_authenticated:
        followed_users = current_user.followed.all()
        followed_ids = [user.id for user in followed_users]
        followed_ids.append(current_user.id)  # Include own blogs
        
        follower_blogs = Blog.query.filter(
            Blog.user_id.in_(followed_ids),
            Blog.is_public == False
        ).order_by(Blog.date_created.desc()).limit(3).all()
        
        # Combine and sort by date
        all_blogs = list(set(recent_blogs + follower_blogs))
        all_blogs.sort(key=lambda x: x.date_created, reverse=True)
        recent_blogs = all_blogs[:6]
    
    return render_template('index.html', featured_blogs=featured_blogs, recent_blogs=recent_blogs)

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            # In a real application, you would send an email here
            flash('Password reset instructions have been sent to your email.', 'info')
        else:
            flash('Email address not found.', 'danger')
        return redirect(url_for('login'))
    
    return render_template('auth/forgot_password.html', form=form)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('profile', username=current_user.username))
        else:
            flash('Current password is incorrect.', 'danger')
    
    return render_template('auth/change_password.html', form=form)

# Profile routes
@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # Get user's blogs
    if current_user.is_authenticated and (current_user.id == user.id or current_user.is_following(user)):
        blogs = user.blogs.order_by(Blog.date_created.desc()).all()
    else:
        blogs = user.blogs.filter_by(is_public=True).order_by(Blog.date_created.desc()).all()
    
    return render_template('user/profile.html', user=user, blogs=blogs)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username, current_user.email)
    
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data.lower()
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.bio = form.bio.data
        
        if form.profile_picture.data:
            picture_file = save_image(form.profile_picture.data, 'profiles', (300, 300))
            current_user.profile_picture = picture_file
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile', username=current_user.username))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.bio.data = current_user.bio
    
    return render_template('user/edit_profile.html', form=form)

# Blog routes
@app.route('/create_blog', methods=['GET', 'POST'])
@login_required
def create_blog():
    form = BlogForm()
    if form.validate_on_submit():
        blog = Blog(
            title=form.title.data,
            subtitle=form.subtitle.data,
            content=form.content.data,
            is_public=form.is_public.data,
            author=current_user
        )
        
        if form.cover_image.data:
            cover_file = save_image(form.cover_image.data, 'covers', (1200, 800))
            blog.cover_image = cover_file
        
        db.session.add(blog)
        db.session.commit()
        
        flash('Blog created successfully!', 'success')
        return redirect(url_for('view_blog', id=blog.id))
    
    return render_template('blog/create.html', form=form)

@app.route('/blog/<int:id>', methods=['GET'])
def view_blog(id):
    blog = Blog.query.get_or_404(id)

    if not blog.can_view(current_user):
        flash("You don't have permission to view this blog.", "danger")
        return redirect(url_for('index'))

    comment_form = CommentForm()
    comments = blog.comments.order_by(Comment.date_created.desc()).all()

    return render_template('blog/view.html', blog=blog, comment_form=comment_form, comments=comments)


@app.route('/edit_blog/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_blog(id):
    blog = Blog.query.get_or_404(id)
    
    if blog.author != current_user:
        flash('You can only edit your own blogs.', 'danger')
        return redirect(url_for('view_blog', id=id))
    
    form = BlogForm()
    if form.validate_on_submit():
        blog.title = form.title.data
        blog.subtitle = form.subtitle.data
        blog.content = form.content.data
        blog.is_public = form.is_public.data
        blog.date_updated = datetime.utcnow()
        
        if form.cover_image.data:
            cover_file = save_image(form.cover_image.data, 'covers', (1200, 800))
            blog.cover_image = cover_file
        
        db.session.commit()
        flash('Blog updated successfully!', 'success')
        return redirect(url_for('view_blog', id=id))
    
    elif request.method == 'GET':
        form.title.data = blog.title
        form.subtitle.data = blog.subtitle
        form.content.data = blog.content
        form.is_public.data = blog.is_public
    
    return render_template('blog/edit.html', form=form, blog=blog)

@app.route('/delete_blog/<int:id>', methods=['POST'])
@login_required
def delete_blog(id):
    blog = Blog.query.get_or_404(id)
    
    if blog.author != current_user:
        flash('You can only delete your own blogs.', 'danger')
        return redirect(url_for('view_blog', id=id))
    
    db.session.delete(blog)
    db.session.commit()
    
    flash('Blog deleted successfully.', 'success')
    return redirect(url_for('profile', username=current_user.username))

@app.route('/toggle_follow/<username>', methods=['POST'])
@login_required
def toggle_follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({'error': 'User not found'}), 404
    
    if user == current_user:
        return jsonify({'error': 'You cannot follow yourself'}), 400
    
    if current_user.is_following(user):
        current_user.unfollow(user)
        db.session.commit()
        return jsonify({'status': 'unfollowed', 'followers_count': user.followers.count()})
    else:
        current_user.follow(user)
        db.session.commit()
        return jsonify({'status': 'followed', 'followers_count': user.followers.count()})

@app.route('/toggle_like_blog/<int:id>', methods=['POST'])
@login_required
def toggle_like_blog(id):
    blog = Blog.query.get_or_404(id)
    
    if current_user.has_liked_blog(blog):
        current_user.unlike_blog(blog)
        db.session.commit()
        return jsonify({'status': 'unliked', 'likes_count': blog.likes_count})
    else:
        current_user.like_blog(blog)
        db.session.commit()
        return jsonify({'status': 'liked', 'likes_count': blog.likes_count})

@app.route('/toggle_like_comment/<int:id>', methods=['POST'])
@login_required
def toggle_like_comment(id):
    comment = Comment.query.get_or_404(id)
    
    if current_user.has_liked_comment(comment):
        current_user.unlike_comment(comment)
        db.session.commit()
        return jsonify({'status': 'unliked', 'likes_count': comment.likes_count})
    else:
        current_user.like_comment(comment)
        db.session.commit()
        return jsonify({'status': 'liked', 'likes_count': comment.likes_count})

@app.route('/add_comment/<int:blog_id>', methods=['POST'])
@login_required
def add_comment(blog_id):
    blog = Blog.query.get_or_404(blog_id)
    form = CommentForm()
    
    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data,
            author=current_user,
            blog=blog
        )
        db.session.add(comment)
        db.session.commit()
        
        utc_time = comment.date_created
        manila_tz = timezone('Asia/Manila')
        manila_time = utc_time.replace(tzinfo=timezone('UTC')).astimezone(manila_tz)

        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author': comment.author.full_name,
                'date': manila_time.strftime('%B %d, %Y at %I:%M %p'),
                'likes_count': 0
            }
        })
    
    return jsonify({'success': False, 'errors': form.errors})

@app.route('/delete_comment/<int:id>', methods=['POST'])
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    blog_id = comment.blog_id
    
    # Check if current user can delete this comment (comment author or blog owner)
    if current_user.id != comment.user_id and current_user.id != comment.blog.user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Comment deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to delete comment'}), 500

@app.route('/dashboard')
@login_required
def dashboard():
    """User's personal dashboard"""
    user_blogs = current_user.blogs.order_by(Blog.date_created.desc()).all()
    return render_template('blog/dashboard.html', blogs=user_blogs)

@app.route('/explore')
def explore():
    """Explore all public blogs"""
    page = request.args.get('page', 1, type=int)
    blogs = Blog.query.filter_by(is_public=True).order_by(Blog.date_created.desc()).paginate(
        page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    
    return render_template('blog/explore.html', blogs=blogs)

# Template filters
@app.template_filter('datetime')
def datetime_filter(datetime_obj):
    return datetime_obj.strftime('%B %d, %Y')

@app.template_filter('current_year')
def current_year_filter(s):
    return datetime.now().year

# Context processors
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# Create tables
with app.app_context():
    db.create_all()
    
    # Create default profile image directory
    os.makedirs(os.path.join(app.root_path, 'static/uploads/profiles'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static/uploads/covers'), exist_ok=True)

if __name__ == '__main__':
    app.run(debug=True)