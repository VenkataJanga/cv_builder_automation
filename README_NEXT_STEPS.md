# MVP1 Next Steps Verification

## Step 1 - Update questionnaire YAML
Replace:
- config/questionnaire/question_bank.yaml

This adds:
- full name
- current location
- professional summary

## Step 2 - Update answer mapper
Replace:
- src/questionnaire/mappers/answer_to_cv_field_mapper.py

This maps the new questions into:
- personal_details.full_name
- personal_details.location
- summary.professional_summary

## Step 3 - Update conversation service
Replace:
- src/application/services/conversation_service.py

This returns `cv_schema_ready` while progressing through questions.

## Step 4 - Add template engine
Add or replace:
- src/infrastructure/rendering/template_engine.py

This creates template-friendly render context from structured CV data.

## Expected outcome
After answering:
- role
- full name
- location
- professional summary
- total experience
- organization
- skills

`cv_schema_ready` should become true.
