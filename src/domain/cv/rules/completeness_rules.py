def check_completeness(cv_data):
    errors=[]
    pd=cv_data.get('personal_details',{})
    summary=cv_data.get('summary',{})
    skills=cv_data.get('skills',{})
    if not pd.get('full_name'): errors.append('Full name required')
    if not pd.get('location'): errors.append('Location required')

    summary_text = ''
    if isinstance(summary, dict):
        summary_text = str(summary.get('professional_summary', '')).strip()
    elif isinstance(summary, list):
        summary_text = ' '.join(
            str(item.get('professional_summary', '')).strip() if isinstance(item, dict) else str(item).strip()
            for item in summary
        ).strip()
    else:
        summary_text = str(summary).strip()

    if not summary_text: errors.append('Summary required')
    
    # Handle skills as list or dict
    skills_present = False
    if isinstance(skills, list):
        skills_present = bool(skills)
    elif isinstance(skills, dict):
        skills_present = bool(skills.get('primary_skills'))
    
    if not skills_present: errors.append('Skills required')
    return errors
