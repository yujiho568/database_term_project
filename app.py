from flask import Flask, render_template, redirect, url_for, request, session, flash
from database import initialize_tables, get_connection
from psycopg2.extras import RealDictCursor
import bcrypt

app = Flask(__name__)
app.secret_key = 'mysecretkey'

initialize_tables()

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, password, user_role FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()


            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['user_role'] = user[3]

                cursor.close()
                conn.close()


                return redirect(url_for('community'))
            else:
                flash("Invalid id or password", "danger")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['user_id']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO users (user_id,username, email, password) 
                    VALUES (%s, %s, %s, %s)
                """, (user_id,username, email, hashed_password))
                conn.commit()
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for('login'))
            except Exception as e:
                conn.rollback()
                flash(f"Error: {e}", "danger")
            finally:
                cursor.close()
                conn.close()
    return render_template('register.html')


@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if request.method == 'POST':
        user_id = session['user_id']
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    DELETE FROM users where user_id = %s
                """, (user_id,))
                conn.commit()
                return redirect(url_for('login'))
            except Exception as e:
                conn.rollback()
                flash(f"Error: {e}", "danger")
            finally:
                cursor.close()
                conn.close()
    return render_template('login.html')

@app.route('/community', methods=['GET'])
def community():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
                    SELECT info_id, info_user_id, location, description, recommended, info_created_at, is_honored
                    FROM post_view
                    ORDER BY info_created_at DESC
                """)
        posts = cursor.fetchall()
        cursor.execute("""
                    SELECT announcement_id,title, content, created_at
                    FROM announcement_view
                    ORDER BY created_at DESC
                """)
        announcements = cursor.fetchall()
        cursor.execute("""
                    SELECT task,title, content, created_at
                    FROM analysis_view
                    ORDER BY created_at DESC
                """)
        analysis = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template('community.html', posts=posts, announcements=announcements, analysis=analysis)

@app.route('/user_info', methods=['GET', 'POST'])
def view_users():
    if 'user_id' not in session:
        flash("You are not authorized", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM user_info_view ORDER BY trust_score DESC")
        user_by_trust = cursor.fetchall()

        cursor.execute("SELECT * FROM user_info_view ORDER BY reported DESC")
        user_by_reported = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template('user_info.html', user_by_trust=user_by_trust, user_by_reported=user_by_reported)

@app.route('/post/<int:info_id>', methods=['GET', 'POST'])
def view_post(info_id):
    conn = get_connection()
    cursor = conn.cursor()
    if request.method == 'POST':

        if 'user_id' not in session:
            flash("Please log in to comment!")
            return redirect('/login')

        comment_content = request.form['comment_content']
        user_id = session['user_id']

        try:
            cursor.execute("""
                INSERT INTO comment (info_id, user_id, comment_content)
                VALUES (%s, %s, %s)
            """, (info_id, user_id, comment_content))
            conn.commit()
            flash("Comment added successfully!")
        except Exception as e:
            conn.rollback()
            flash(f"Error adding comment: {e}")
    try:
        cursor.execute("""
            SELECT location, description, people_count, recommended, created_at, latitude, longitude
            FROM information
            WHERE info_id = %s
        """, (info_id,))
        post = cursor.fetchone()


        cursor.execute("""
            SELECT c.comment_content, u.user_id, c.created_at, c.comment_id
            FROM comment c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.info_id = %s
            ORDER BY c.created_at ASC
        """, (info_id,))
        comments = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template('view_post.html', post=post, comments=comments, info_id=info_id)

@app.route('/recommend/<int:info_id>', methods=['POST'])
def recommend_post(info_id):
    if 'user_id' not in session:
        flash("Please log in to recommend.", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    try:

        cursor.execute("""
            UPDATE information
            SET recommended = recommended + 1
            WHERE info_id = %s
        """, (info_id,))
        cursor.execute("""
            UPDATE users
            SET trust_score = trust_score + 1
            WHERE user_id = (
                SELECT user_id
                FROM information
                WHERE info_id = %s
            )
        """, (info_id,))

        conn.commit()
        flash("Successfully recommended the post!", "success")
        return redirect(f'/post/{info_id}')
    except Exception as e:
        conn.rollback()
        flash(f"Error recommending post: {e}", "danger")
        return redirect('/community')
    finally:
        cursor.close()
        conn.close()


@app.route('/report/<int:info_id>', methods=['POST'])
def report_user(info_id):
    if 'user_id' not in session:
        flash("Please log in to recommend.", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    try:

        cursor.execute("""
            UPDATE users
            SET reported = reported + 1
            WHERE user_id = (
                SELECT user_id
                FROM information
                WHERE info_id = %s
            )
        """, (info_id,))

        conn.commit()
        flash("Successfully reported the user!", "success")
        return redirect(f'/post/{info_id}')
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
        return redirect('/community')
    finally:
        cursor.close()
        conn.close()

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash("Please log in to create a post!")
        return redirect('/login')

    if request.method == 'POST':
        user_id = session['user_id']
        location = request.form['location']
        description = request.form['description']
        people_count = request.form['people_count']
        latitude = request.form['latitude']
        longitude = request.form['longitude']

        # Validate latitude and longitude
        if not latitude or not longitude:
            flash("Please select a location on the map.", "danger")
            return redirect('/create_post')

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO information (user_id, location, latitude, longitude, description, people_count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, location, float(latitude), float(longitude), description, people_count))

            conn.commit()

            flash("Post created successfully!", "success")
            return redirect('/community')
        except Exception as e:
            conn.rollback()
            flash(f"Error creating post: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template('create_post.html')

@app.route('/edit_post/<int:info_id>', methods=['GET', 'POST'])
def edit_post(info_id):
    if 'user_id' not in session:
        flash("Please log in to edit a post!", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 작성자 확인
        cursor.execute("SELECT user_id, location, description FROM information WHERE info_id = %s", (info_id,))
        post = cursor.fetchone()

        if not post or post[0] != session['user_id']:
            flash("You are not authorized to edit this post!", "danger")
            return redirect('/community')

        if request.method == 'POST':
            location = request.form['location']
            description = request.form['description']

            cursor.execute("""
                UPDATE information
                SET location = %s, description = %s, updated_at = CURRENT_TIMESTAMP
                WHERE info_id = %s
            """, (location, description, info_id))
            conn.commit()
            flash("Post updated successfully!", "success")
            return redirect('/community')
    except Exception as e:
        conn.rollback()
        flash(f"Error editing post: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return render_template('edit_post.html', post=post)

@app.route('/delete_post/<int:info_id>', methods=['POST'])
def delete_post(info_id):
    if 'user_id' not in session:
        flash("Please log in to delete a post!", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 작성자 확인
        cursor.execute("SELECT user_id FROM information WHERE info_id = %s", (info_id,))
        post = cursor.fetchone()

        if not post or post[0] != session['user_id']:
            flash("You are not authorized to delete this post!", "danger")
            return redirect('/community')

        cursor.execute("DELETE FROM information WHERE info_id = %s", (info_id,))
        conn.commit()
        flash("Post deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting post: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/community')

@app.route('/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
def edit_comment(comment_id):
    if 'user_id' not in session:
        flash("Please log in to edit a comment!", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 작성자 확인
        cursor.execute("SELECT user_id, comment_content FROM comment WHERE comment_id = %s", (comment_id,))
        comment = cursor.fetchone()

        if not comment or comment[0] != session['user_id']:
            flash("You are not authorized to edit this comment!", "danger")
            return redirect('/community')

        if request.method == 'POST':
            new_content = request.form['comment_content']

            cursor.execute("""
                UPDATE comment
                SET comment_content = %s, updated_at = CURRENT_TIMESTAMP
                WHERE comment_id = %s
            """, (new_content, comment_id))
            conn.commit()
            flash("Comment updated successfully!", "success")
            return redirect('/community')
    except Exception as e:
        conn.rollback()
        flash(f"Error editing comment: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return render_template('edit_comment.html', comment=comment)

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        flash("Please log in to delete a comment!", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 작성자 확인
        cursor.execute("SELECT user_id FROM comment WHERE comment_id = %s", (comment_id,))
        comment = cursor.fetchone()

        if not comment or comment[0] != session['user_id']:
            flash("You are not authorized to delete this comment!", "danger")
            return redirect('/community')

        cursor.execute("DELETE FROM comment WHERE comment_id = %s", (comment_id,))
        conn.commit()
        flash("Comment deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting comment: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/community')

@app.route('/create_announcement', methods=['GET', 'POST'])
def create_announcement():

    if 'user_role' not in session or session['user_role'] != 'admin':
        flash("Only admins can create announcements!", "danger")
        return redirect('/community')

    if request.method == 'POST':
        admin_id = session['user_id']
        title = request.form['title']
        content = request.form['content']

        conn = get_connection()
        cursor = conn.cursor()
        if session['user_role'] == 'admin':
            cursor.execute("SET ROLE admin;")
        elif session['user_role'] == 'user':
            cursor.execute("SET ROLE reg_user;")
        elif session['user_role'] == 'analyst':
            cursor.execute("SET ROLE analyst;")
        try:

            cursor.execute("""
                SELECT grantee, privilege_type
                FROM information_schema.role_table_grants
                WHERE table_name IN ('users', 'information', 'analysis', 'comment', 'announcement');
            """)
            data = cursor.fetchall()
            print(data)
            cursor.execute("""
                INSERT INTO announcement (admin_id, title, content)
                VALUES (%s, %s, %s)
            """, (admin_id, title, content))
            conn.commit()
            flash("Announcement created successfully!", "success")
            return redirect('/community')
        except Exception as e:
            conn.rollback()
            flash(f"Error creating announcement: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template('create_announcement.html')


@app.route('/delete_announcement/<int:announcement_id>', methods=['POST'])
def delete_announcement(announcement_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash("You have no rights to delete announcement!", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    if session['user_role'] == 'admin':
        cursor.execute("SET ROLE admin;")
    elif session['user_role'] == 'user':
        cursor.execute("SET ROLE reg_user;")
    elif session['user_role'] == 'analyst':
        cursor.execute("SET ROLE analyst;")
    try:
        # 작성자 확인
        cursor.execute("SELECT admin_id FROM announcement WHERE announcement_id = %s", (announcement_id,))
        announcement = cursor.fetchone()

        if not announcement:
            return redirect('/community')

        cursor.execute("DELETE FROM announcement WHERE announcement_id = %s", (announcement_id,))
        conn.commit()
        flash("Announcement deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting announcement: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/community')


@app.route('/create_analysis', methods=['GET', 'POST'])
def create_analysis():

    if 'user_role' not in session or session['user_role'] != 'analyst':
        flash("Only analysts can create analysis!", "danger")
        return redirect('/community')

    if request.method == 'POST':
        analyst_id = session['user_id']
        title = request.form['title']
        content = request.form['content']
        conn = get_connection()
        cursor = conn.cursor()
        if session['user_role'] == 'admin':
            cursor.execute("SET ROLE admin;")
        elif session['user_role'] == 'user':
            cursor.execute("SET ROLE reg_user;")
        elif session['user_role'] == 'analyst':
            cursor.execute("SET ROLE analyst;")
        try:

            cursor.execute("""
                INSERT INTO analysis (analyst_id, title, content)
                VALUES (%s, %s, %s)
            """, (analyst_id, title, content))
            conn.commit()
            flash("Analysis created successfully!", "success")
            return redirect('/community')
        except Exception as e:
            conn.rollback()
            flash(f"Error creating analysis: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template('create_analysis.html')


@app.route('/honor_user/<string:user_id>', methods=['POST'])
def honor_user(user_id):
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash("You have no rights to delete announcement!", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    if session['user_role'] == 'admin':
        cursor.execute("SET ROLE admin;")
    elif session['user_role'] == 'user':
        cursor.execute("SET ROLE reg_user;")
    elif session['user_role'] == 'analyst':
        cursor.execute("SET ROLE analyst;")
    try:

        cursor.execute("""
            UPDATE users
            SET is_honored = TRUE
            WHERE user_id = %s
        """,(user_id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/community')


@app.route('/grant_analyst/<string:user_id>', methods=['POST'])
def grant_analyst(user_id):
    if 'user_id' not in session or session['user_role'] != 'analyst':
        flash("You have no rights to delete announcement!", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    if session['user_role'] == 'admin':
        cursor.execute("SET ROLE admin;")
    elif session['user_role'] == 'user':
        cursor.execute("SET ROLE reg_user;")
    elif session['user_role'] == 'analyst':
        cursor.execute("SET ROLE analyst;")
    try:
        cursor.execute("""
            SELECT user_role
            FROM users
            WHERE user_id = %s
        """, (user_id,))

        role = cursor.fetchall()
        if role!='admin':
            cursor.execute("""
                UPDATE users
                SET user_role = 'analyst'
                WHERE user_id = %s
            """,(user_id,))

        conn.commit()

    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/community')

@app.route('/delete_analysis/<int:task>', methods=['POST'])
def delete_analysis(task):
    if 'user_id' not in session or session['user_role'] == 'user':
        flash("You have no rights to delete analysis!", "danger")
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    if session['user_role'] == 'admin':
        cursor.execute("SET ROLE admin;")
    elif session['user_role'] == 'user':
        cursor.execute("SET ROLE reg_user;")
    elif session['user_role'] == 'analyst':
        cursor.execute("SET ROLE analyst;")
    try:
        cursor.execute("SELECT analyst_id FROM analysis WHERE task = %s", (task,))
        analyst_id = cursor.fetchone()

        if not analyst_id:
            return redirect('/community')

        cursor.execute("DELETE FROM analysis WHERE analyst_id = %s", (analyst_id,))
        conn.commit()
        flash("Announcement deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting announcement: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect('/community')

if __name__ == '__main__':
    app.run(debug=True)