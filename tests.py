
import os
import sys
import sqlite3


os.environ['DATABASE'] = 'test.db'
if os.path.exists('test.db'):
    os.remove('test.db')

import database
database.DATABASE = 'test.db'

from app import app, init_db
from scoring import score



failures = []


def check(name, condition):
    if condition:
        print(f'  PASS: {name}')
    else:
        print(f'  FAIL: {name}')
        failures.append(name)


def mk_cand(**kw):
    #build candidate dict for scoring
    base = {'skills': '', 'preferred_location': '', 'preferred_mode': '',
            'years_experience': 0, 'education': ''}
    base.update(kw)
    return base


def mk_job(**kw):
    #build job dict for test scoring
    base = {'required_skills': '', 'location': '', 'work_mode': '',
            'years_experience': 0, 'required_education': ''}
    base.update(kw)
    return base


#scoring tests
def test_scoring():
    print('\n=== Scoring (unit tests) ===')

    # Empty input
    s, _ = score(mk_cand(), mk_job())
    check('empty cand/job scores 10 (exp baseline only)', s == 10)

    # Perfect match
    s, r = score(
        mk_cand(skills='python,sql,react', preferred_location='Boston',
                preferred_mode='Remote', years_experience=5, education='Bachelor'),
        mk_job(required_skills='python,sql,react', location='Boston',
               work_mode='Remote', years_experience=2, required_education='Bachelor')
    )
    check('perfect match scores 70', s == 70)
    check('reasons list has 5 entries', len(r) == 5)

    # Skill formatting
    s, _ = score(mk_cand(skills='Python, SQL , REACT'),
                 mk_job(required_skills='python,sql,react'))
    check('skill case/whitespace normalized', s == 40)  # 30 + 10 exp

    # Not enough experience
    s, _ = score(mk_cand(years_experience=1), mk_job(years_experience=5))
    check('under-experienced scores 0', s == 0)

    # Wrong location
    s, _ = score(mk_cand(preferred_location='Boston'), mk_job(location='NYC'))
    check('location mismatch — only exp baseline', s == 10)

    # Wrong education
    s, _ = score(mk_cand(education='Master'), mk_job(required_education='Bachelor'))
    check('wrong education — only exp baseline', s == 10)

    # Blank work_mode should NOT match blank work_mode
    s, _ = score(mk_cand(preferred_mode=''), mk_job(work_mode=''))
    check('blank mode does not falsely match blank', s == 10)  # only exp


#integration tests
def test_integration():
    print('\n=== Integration (test_client) ===')
    init_db(app)
    c = app.test_client()

    #Signup + login
    r = c.post('/signup/employer',
               data={'email': 'bob@co.com', 'password': 'pw'},
               follow_redirects=True)
    check('employer signup returns 200', r.status_code == 200)

    r = c.post('/login',
               data={'email': 'bob@co.com', 'password': 'wrong'})
    check('wrong password rejected', 'Invalid' in r.get_data(as_text=True))

    r = c.post('/login',
               data={'email': 'bob@co.com', 'password': 'pw'},
               follow_redirects=True)
    check('correct login succeeds', 'Welcome back' in r.get_data(as_text=True))

    # postnig a job
    r = c.post('/jobs/new',
               data={'title': 'Backend Engineer',
                     'description': 'Build APIs with Python and SQL.',
                     'company': 'Acme', 'required_education': 'Bachelor',
                     'required_skills': 'python,sql,docker',
                     'years_experience': '2', 'work_mode': 'Remote',
                     'location': 'Boston'},
               follow_redirects=True)
    check('job posting returns 200', r.status_code == 200)

    db = sqlite3.connect('test.db')
    db.row_factory = sqlite3.Row
    job = db.execute('SELECT * FROM jobs WHERE title=?',
                     ('Backend Engineer',)).fetchone()
    check('job row persisted with correct fields',
          job is not None and job['required_skills'] == 'python,sql,docker')
    bob_job_id = job['id']

    #candidate signup
    c.get('/logout')
    c.post('/signup/candidate',
           data={'email': 'alice@x.com', 'password': 'pw',
                 'full_name': 'Alice', 'contact': '',
                 'education': 'Bachelor', 'major': 'CS',
                 'years_experience': '3', 'work_experience': '',
                 'skills': 'python,sql,docker',
                 'preferred_mode': 'Remote',
                 'preferred_location': 'Boston'})
    cand = db.execute('SELECT * FROM candidates WHERE full_name=?',
                      ('Alice',)).fetchone()
    check('candidate row persisted', cand is not None)

    #Access control test
    c.post('/login', data={'email': 'alice@x.com', 'password': 'pw'})
    r = c.get('/jobs/new', follow_redirects=False)
    check('candidate blocked from /jobs/new', r.status_code == 302)

    r = c.get('/candidates', follow_redirects=False)
    check('candidate blocked from /candidates', r.status_code == 302)

    #displaying listings
    r = c.get('/jobs')
    check('candidate sees jobs listing', 'Backend Engineer' in r.get_data(as_text=True))

    # search functionality
    r = c.get('/jobs?q=python')
    check('search returns matches', 'Backend Engineer' in r.get_data(as_text=True))

    r = c.get('/jobs?q=nonexistent_xyz')
    check('no-match shows empty state',
          'No jobs match' in r.get_data(as_text=True))

    # recommendation for candidates
    r = c.get('/jobs/recommended')
    html = r.get_data(as_text=True)
    check('candidate gets recommendations', 'Backend Engineer' in html)
    check('match score rendered', 'Match: 70' in html)
    check('recommendation shows job skills', 'python,sql,docker' in html)

    # recommendations for remployers
    c.get('/logout')
    c.post('/login', data={'email': 'bob@co.com', 'password': 'pw'})
    r = c.get('/candidates/recommended')
    html = r.get_data(as_text=True)
    check('employer sees recommendations', 'Alice' in html)
    check('match score rendered for employer', 'Match: 70' in html)

    # Queries are locked behind unique identifiers
    c.get('/logout')
    c.post('/signup/employer', data={'email': 'eve@hack.com', 'password': 'pw'})
    c.post('/login', data={'email': 'eve@hack.com', 'password': 'pw'})
    r = c.get(f'/jobs/{bob_job_id}/edit')
    check('IDOR: foreign employer GET edit -> 404', r.status_code == 404)

    r = c.post(f'/jobs/{bob_job_id}/delete')
    check('IDOR: foreign employer DELETE -> 404', r.status_code == 404)

    job_after = db.execute('SELECT * FROM jobs WHERE id=?',
                           (bob_job_id,)).fetchone()
    check('IDOR: target job unchanged after attack',
          job_after['title'] == 'Backend Engineer')


    c.get('/logout')
    r = c.get('/dashboard', follow_redirects=False)
    check('anonymous /dashboard -> /login',
          r.status_code == 302 and '/login' in r.headers.get('Location', ''))

    db.close()



if __name__ == '__main__':
    test_scoring()
    test_integration()

    print('\n' + '=' * 40)
    if failures:
        print(f'FAILED: {len(failures)} test(s)')
        for f in failures:
            print(f'  - {f}')
        sys.exit(1)
    else:
        print('All tests passed.')
        sys.exit(0)