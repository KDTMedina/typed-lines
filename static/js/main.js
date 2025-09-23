// Main JavaScript for TypedLines

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Quill editor if present
    initializeQuillEditor();
    
    // Initialize like buttons
    initializeLikeButtons();
    
    // Initialize follow buttons
    initializeFollowButtons();
    
    // Initialize comment system
    initializeCommentSystem();
    
    // Initialize image preview
    initializeImagePreview();
    
    // Auto-hide alerts
    autoHideAlerts();
});

// Quill Rich Text Editor
function initializeQuillEditor() {
    const editorElement = document.getElementById('editor');
    if (editorElement) {
        const quill = new Quill('#editor', {
            theme: 'snow',
            placeholder: 'Start writing your story...',
            modules: {
                toolbar: [
                    [{ 'header': [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ 'color': [] }, { 'background': [] }],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    [{ 'align': [] }],
                    ['blockquote', 'code-block'],
                    ['link', 'image'],
                    ['clean']
                ]
            }
        });

        // Sync Quill content with form field
        const contentField = document.getElementById('content');
        if (contentField) {
            // Set initial content
            if (contentField.value) {
                quill.root.innerHTML = contentField.value;
            }
            
            // Update hidden field on content change
            quill.on('text-change', function() {
                contentField.value = quill.root.innerHTML;
            });
        }
    }
}

// Like System
function initializeLikeButtons() {
    const likeButtons = document.querySelectorAll('[data-like-type]');
    
    likeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const likeType = this.dataset.likeType;
            const itemId = this.dataset.itemId;
            const countElement = this.querySelector('.like-count');
            
            // Disable button during request
            this.disabled = true;
            
            let url;
            if (likeType === 'blog') {
                url = `/toggle_like_blog/${itemId}`;
            } else if (likeType === 'comment') {
                url = `/toggle_like_comment/${itemId}`;
            }
            
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                // Update like count
                if (countElement) {
                    countElement.textContent = data.likes_count;
                }
                
                // Update button appearance
                const icon = this.querySelector('i');
                if (data.status === 'liked') {
                    this.classList.add('liked');
                    icon.classList.remove('bi-heart');
                    icon.classList.add('bi-heart-fill');
                } else {
                    this.classList.remove('liked');
                    icon.classList.remove('bi-heart-fill');
                    icon.classList.add('bi-heart');
                }
                
                // Re-enable button
                this.disabled = false;
            })
            .catch(error => {
                console.error('Error:', error);
                this.disabled = false;
                showToast('Error updating like', 'error');
            });
        });
    });
}

// Follow System
function initializeFollowButtons() {
    const followButtons = document.querySelectorAll('[data-follow-username]');
    
    followButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const username = this.dataset.followUsername;
            const countElement = document.querySelector('.followers-count');
            
            // Disable button during request
            this.disabled = true;
            
            fetch(`/toggle_follow/${username}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showToast(data.error, 'error');
                    return;
                }
                
                // Update followers count
                if (countElement) {
                    countElement.textContent = data.followers_count;
                }
                
                // Update button text and appearance
                if (data.status === 'followed') {
                    this.textContent = 'Unfollow';
                    this.classList.remove('btn-outline-olive');
                    this.classList.add('btn-olive', 'following');
                } else {
                    this.textContent = 'Follow';
                    this.classList.remove('btn-olive', 'following');
                    this.classList.add('btn-outline-olive');
                }
                
                // Re-enable button
                this.disabled = false;
            })
            .catch(error => {
                console.error('Error:', error);
                this.disabled = false;
                showToast('Error updating follow status', 'error');
            });
        });
    });
}

// Comment System
function initializeCommentSystem() {
    const commentForm = document.getElementById('comment-form');
    
    if (commentForm) {
        commentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const blogId = this.dataset.blogId;
            const submitButton = this.querySelector('button[type="submit"]');
            const contentField = this.querySelector('#content');
            
            // Disable submit button
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Posting...';
            
            fetch(`/add_comment/${blogId}`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Add new comment to the page
                    const commentsContainer = document.getElementById('comments-container');
                    const newComment = createCommentElement(data.comment);
                    
                    if (commentsContainer.children.length === 0) {
                        commentsContainer.appendChild(newComment);
                    } else {
                        commentsContainer.insertBefore(newComment, commentsContainer.firstChild);
                    }
                    
                    // Clear form
                    contentField.value = '';
                    
                    // Show success message
                    showToast('Comment posted successfully!', 'success');
                } else {
                    showToast('Error posting comment', 'error');
                }
                
                // Re-enable submit button
                submitButton.disabled = false;
                submitButton.innerHTML = 'Post Comment';
            })
            .catch(error => {
                console.error('Error:', error);
                submitButton.disabled = false;
                submitButton.innerHTML = 'Post Comment';
                showToast('Error posting comment', 'error');
            });
        });
    }
}

// Create comment element
function createCommentElement(comment) {
    const commentDiv = document.createElement('div');
    commentDiv.className = 'comment-item fade-in';
    commentDiv.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div>
                <span class="comment-author">${comment.author}</span>
                <span class="comment-date ms-2">${comment.date}</span>
            </div>
            <button class="like-btn" data-like-type="comment" data-item-id="${comment.id}">
                <i class="bi bi-heart me-1"></i>
                <span class="like-count">${comment.likes_count}</span>
            </button>
        </div>
        <p class="mt-2 mb-0">${comment.content}</p>
    `;
    
    // Initialize like button for new comment
    const likeButton = commentDiv.querySelector('.like-btn');
    likeButton.addEventListener('click', function(e) {
        e.preventDefault();
        // Re-initialize like functionality for this button
        initializeLikeButtons();
    });
    
    return commentDiv;
}

// Image Preview
function initializeImagePreview() {
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    
    imageInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    let preview = document.getElementById(input.id + '-preview');
                    
                    if (!preview) {
                        preview = document.createElement('img');
                        preview.id = input.id + '-preview';
                        preview.className = 'img-fluid mt-2 rounded';
                        preview.style.maxWidth = '300px';
                        input.parentNode.appendChild(preview);
                    }
                    
                    preview.src = e.target.result;
                };
                
                reader.readAsDataURL(file);
            }
        });
    });
}

// Auto-hide alerts
function autoHideAlerts() {
    const alerts = document.querySelectorAll('.alert');

    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade');
            setTimeout(() => {
                alert.remove();
            }, 500); // Wait for fade-out transition
        }, 5000); // Auto-hide after 3 seconds
    });
}
