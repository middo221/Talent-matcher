from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

from database import close_db, init_db, get_db
from auth import current_user, login_required
from scoring import score

app = Flask(__name__)
app.secret_key = 'dev-key'
app.teardown_appcontext(close_db)


#homepage
@app.route('/')
def home():
    return render_template('home.html', user=current_user())


#login auth
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        row = get_db().execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        if row and check_password_hash(row['password_hash'], password):
            session['user_id'] = row['id']
            session['role'] = row['role']
            flash(f'Welcome back, {email}!')
            return redirect(url_for('home'))
        flash('Invalid email or password.')
    return render_template('login.html')


#logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('home'))


#signup for candidates
@app.route('/signup/candidate', methods=['GET', 'POST'])
def signup_candidate():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        try:
            cur = db.execute(
                'INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
                (f['email'].strip().lower(),
                 generate_password_hash(f['password']),
                 'candidate')
            )
            db.execute(
                '''INSERT INTO candidates
                   (user_id, full_name, contact, education, major,
                    years_experience, work_experience, skills,
                    preferred_mode, preferred_location)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (cur.lastrowid,
                 f['full_name'], f['contact'], f['education'], f['major'],
                 int(f.get('years_experience') or 0),
                 f['work_experience'], f['skills'],
                 f['preferred_mode'], f['preferred_location'])
            )
            db.commit()
            flash('Account created. Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            db.rollback()
            flash(f'Could not create account: {e}')
    return render_template('signup-candidate.html')


#signup for employers
@app.route('/signup/employer', methods=['GET', 'POST'])
def signup_employer():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
                (f['email'].strip().lower(),
                 generate_password_hash(f['password']),
                 'employer')
            )
            db.commit()
            flash('Employer account created. Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            db.rollback()
            flash(f'Could not create account: {e}')
    return render_template('signup-employer.html')


#posting a job
@app.route('/jobs/new', methods=['GET', 'POST'])
@login_required(role='employer')
def job_new():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        try:
            db.execute(
                '''INSERT INTO jobs
                   (employer_id, title, description, company,
                    required_education, required_skills,
                    years_experience, work_mode, location)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (session['user_id'],
                 f['title'], f['description'], f['company'],
                 f['required_education'], f['required_skills'],
                 int(f.get('years_experience') or 0),
                 f['work_mode'], f['location'])
            )
            db.commit()
            flash('Job created.')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.rollback()
            flash(f'Could not post job: {e}')
    return render_template('job_form.html')


#employer specific job listing
@app.route('/jobs/mine')
@login_required(role='employer')
def jobs_mine():
    jobs = get_db().execute(
        'SELECT * FROM jobs WHERE employer_id = ? ORDER BY id DESC',
        (session['user_id'],)
    ).fetchall()

    return render_template('jobs_mine.html', jobs=jobs)


#editing a job
@app.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required(role='employer')
def job_edit(job_id):
    db = get_db()

    job = db.execute(
        'SELECT * FROM jobs WHERE id = ? AND employer_id = ?',
        (job_id, session['user_id'])
    ).fetchone()

    if job is None:
        abort(404)

    if request.method == 'POST':
        f = request.form
        try:
            db.execute(
                '''UPDATE jobs SET
                    title = ?, description = ?, company = ?,
                    required_education = ?, required_skills = ?,
                    years_experience = ?, work_mode = ?, location = ?
                    WHERE id = ? AND employer_id = ?''',
                (f['title'], f['description'], f['company'],
                 f['required_education'], f['required_skills'],
                 int(f.get('years_experience') or 0),
                 f['work_mode'], f['location'],
                 job_id, session['user_id'])
            )

            db.commit()
            flash('Job edited.')
            return redirect(url_for('jobs_mine'))
        except Exception as e:
            db.rollback()
            flash(f'Could not edit job: {e}')

    return render_template('job_form.html', record=job)


#delete a job
@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required(role='employer')
def job_delete(job_id):
    db = get_db()
    cur = db.execute(
        'DELETE FROM jobs WHERE id = ? AND employer_id = ?',
        (job_id, session['user_id'])
    )
    db.commit()
    if cur.rowcount == 0:
        abort(404)
    flash('Job deleted.')
    return redirect(url_for('jobs_mine'))


#edit candidate profile
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required(role='candidate')
def profile_edit():
    db = get_db()
    uid = session['user_id']

    if request.method == 'POST':
        f = request.form
        try:
            db.execute(
                '''UPDATE candidates SET
                    full_name = ?, contact = ?, education = ?, major = ?,
                    years_experience = ?, work_experience = ?, skills = ?,
                    preferred_mode = ?, preferred_location = ?
                    WHERE user_id = ?''',
                (f['full_name'], f['contact'], f['education'], f['major'],
                 int(f.get('years_experience') or 0), f['work_experience'],
                 f['skills'], f['preferred_mode'], f['preferred_location'],
                 uid)
            )
            db.commit()
            flash('Profile updated.')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.rollback()
            flash(f'Could not edit profile: {e}')

    record = db.execute(
        'SELECT * FROM candidates WHERE user_id = ?', (uid,)
    ).fetchone()

    return render_template('profile_edit.html', record=record)


#browsing jobs
@app.route('/jobs')
@login_required(role='candidate')
def jobs_browse():
    q = request.args.get('q', '').strip()

    sql = 'SELECT * FROM jobs WHERE 1=1'

    params = []

    if q:
        sql += ' AND LOWER(description) LIKE ?'
        params.append(f'%{q.lower()}%')
    sql += ' ORDER BY id DESC'

    jobs = get_db().execute(sql, params).fetchall()
    return render_template('jobs.html', jobs = jobs)


#employers browsing candidates
@app.route('/candidates')
@login_required(role='employer')
def candidates_browse():
    q = request.args.get('q', '').strip()
    skill = request.args.get('skill', '').strip()
    education = request.args.get('education', '').strip()
    min_years = request.args.get('min_years', '').strip()

    sql = 'SELECT * FROM candidates WHERE 1=1'

    params = []

    if q:
        sql += ' AND LOWER(work_experience) LIKE ?'
        params.append(f'%{q.lower()}%')
    if skill:
        sql += ' AND LOWER(skills) LIKE ?'
        params.append(f'%{skill.lower()}%')
    if education:
        sql += ' AND education = ?'
        params.append(education)
    if min_years:
        try:
            years_int = int(min_years)
            sql += ' AND years_experience >= ?'
            params.append(years_int)
        except ValueError:
            pass
    sql += ' ORDER BY user_id DESC'

    candidates = get_db().execute(sql, params).fetchall()
    return render_template('candidates.html', candidates = candidates)


#recomending a job
TOP_K = 10

@app.route('/jobs/recommended')
@login_required(role='candidate')
def jobs_recommended():
    db = get_db()
    candidate = db.execute(
        'SELECT * FROM candidates WHERE user_id = ?', (session['user_id'],)
    ).fetchone()

    jobs = db.execute('SELECT * FROM jobs').fetchall()

    ranked = []
    for j in jobs:
        s, reason = score(candidate, j)
        if s > 0:
            ranked.append((s, reason, j))

    ranked.sort(key = lambda x: x[0], reverse = True)
    ranked = ranked[:TOP_K]

    return render_template('jobs_recommended.html', ranked = ranked)


#candidate recommended
@app.route('/candidates/recommended')
@login_required(role='employer')
def candidates_recommended():
    db = get_db()
    my_jobs = db.execute(
        'SELECT * FROM jobs WHERE employer_id = ? ORDER BY id DESC', (session['user_id'],)
    ).fetchall()

    if not my_jobs:
        return render_template('candidates_recommended.html', my_jobs = [], selected_job = None, ranked = [])

    #default job to most recent
    job_id = request.args.get('job_id', type = int)
    selected_job = None
    if job_id is not None:
        for j in my_jobs:
            if j['id'] == job_id:
                selected_job = j
                break
    if selected_job is None:
        selected_job = my_jobs[0]

    candidates = db.execute('SELECT * FROM candidates').fetchall()
    ranked = []
    for c in candidates:
        s, reason = score(c, selected_job)
        if s > 0:
            ranked.append((s, reason, c))
    ranked.sort(key = lambda x: x[0], reverse = True)
    ranked = ranked[:TOP_K]

    return render_template('candidates_recommended.html', my_jobs = my_jobs,
                           selected_job = selected_job, ranked = ranked)

#home page
@app.route('/dashboard')
@login_required()
def dashboard():
    user = current_user()
    return render_template('dashboard.html', user=user)




if __name__ == '__main__':
    init_db(app)
    app.run(debug=True)