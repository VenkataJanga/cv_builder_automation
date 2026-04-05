def check_completeness(cv_data):
    errors=[]
    pd=cv_data.get('personal_details',{})
    summary=cv_data.get('summary',{})
    skills=cv_data.get('skills',{})
    if not pd.get('full_name'): errors.append('Full name required')
    if not pd.get('location'): errors.append('Location required')
    if not summary.get('professional_summary'): errors.append('Summary required')
    if not skills.get('primary_skills'): errors.append('Skills required')
    return errors
