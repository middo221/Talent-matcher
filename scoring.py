
# Weight constants
SKILL_WEIGHT = 10
LOCATION_WEIGHT = 15
WORK_MODE_WEIGHT = 10
EXPERIENCE_WEIGHT = 10
EDUCATION_WEIGHT = 5

#transform skills into set
def _to_skill_set(raw):
    if not raw:
        return set()
    return {s.strip().lower() for s in raw.split(',') if s.strip()}

#returns a score for a cnadidate/job pair
def score(candidate, job):
    points = 0
    reasons = []

    #Each matching skill contributes SKILL_WEIGHT points.
    cand_skills = _to_skill_set(candidate['skills'])
    job_skills = _to_skill_set(job['required_skills'])
    overlap = cand_skills & job_skills
    if overlap:
        points += SKILL_WEIGHT * len(overlap)
        reasons.append(f"{len(overlap)} matching skill{'s' if len(overlap) != 1 else ''}: {', '.join(sorted(overlap))}")

    #match by lcation
    if (candidate['preferred_location'] and job['location']
            and candidate['preferred_location'].strip().lower() == job['location'].strip().lower()):
        points += LOCATION_WEIGHT
        reasons.append(f"location matches ({job['location']})")

    #match by work mode
    if (candidate['preferred_mode'] and job['work_mode']
            and candidate['preferred_mode'] == job['work_mode']):
        points += WORK_MODE_WEIGHT
        reasons.append(f"work mode matches ({job['work_mode']})")

    #match by experience
    cand_years = candidate['years_experience'] or 0
    job_years = job['years_experience'] or 0
    if cand_years >= job_years:
        points += EXPERIENCE_WEIGHT
        reasons.append(f"experience sufficient ({cand_years} yrs >= {job_years} required)")

    #match by education
    if (candidate['education'] and job['required_education']
            and candidate['education'] == job['required_education']):
        points += EDUCATION_WEIGHT
        reasons.append(f"education matches ({job['required_education']})")

    return points, reasons