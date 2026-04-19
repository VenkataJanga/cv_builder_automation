from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.ai.services.conversational_text_extractor import extract_from_conversational_text
from src.ai.services.llm_service import get_llm_service
from src.core.logging.logger import get_print_logger
from src.domain.cv.services.merge_cv import MergeCVService


print = get_print_logger(__name__)


class AnswerToCVFieldMapper:
    """
    Maps questionnaire answers into the canonical CV data structure.

    MVP1:
    - Question text based mapping
    - Stores unknown questions in unmapped_answers so data is never lost
    """

    def __init__(self) -> None:
        self._id_to_target: Dict[str, tuple[str, str]] = {}
        self._llm_question_cache: Dict[str, tuple[str, str] | None] = {}
        self._llm_service = get_llm_service()
        self._mapping = {
            "what is your full name?": ("personal_details", "full_name"),
            "what is your current role/title?": ("personal_details", "current_title"),
            "what is your employee or portal id?": ("personal_details", "employee_id"),
            "what is your official email address?": ("personal_details", "email"),
            "what is your current location?": ("personal_details", "location"),
            "how would you describe your professional profile in 2-3 lines?": ("summary", "professional_summary"),
            "how would you describe your professional profile in 2–3 lines?": ("summary", "professional_summary"),
            "what is your total years of experience?": ("personal_details", "total_experience"),
            "what is your current organization?": ("personal_details", "current_organization"),
            "what kinds of roles are you targeting?": ("summary", "target_role"),
            "which industries or domains have you worked in?": ("skills", "domain_expertise"),
            "what are your core areas of expertise?": ("skills", "domain_expertise"),
            "what are your key primary skills?": ("skills", "primary_skills"),
            "what are your secondary skills or supporting technologies?": ("skills", "secondary_skills"),
            "which tools, platforms, databases, cloud services, or operating systems have you worked with?": ("skills", "tools_and_platforms"),
            "what certifications do you hold?": ("certifications", "certifications"),
            "please share your educational qualifications.": ("education", "education"),
            "which languages do you speak or write?": ("languages", "languages"),
            "have you led teams? if yes, what was the team size?": ("leadership", "team_leadership"),
            "what are your key leadership achievements?": ("leadership", "leadership_achievements"),
            "what business outcomes have you delivered?": ("leadership", "business_outcomes"),
            "what was your role in project execution?": ("leadership", "execution_role"),
            "how did you manage your team’s performance?": ("leadership", "team_performance"),
            "what technologies or tools did your team use?": ("leadership", "technologies_tools"),
            "how did you handle delivery challenges?": ("leadership", "delivery_challenges"),
            "did you mentor or coach team members?": ("leadership", "mentoring"),
            "how did you ensure code quality or delivery quality?": ("leadership", "quality_assurance"),
            "have you handled sprint planning or agile ceremonies?": ("leadership", "agile_ceremonies"),
            "what improvements did you bring to your team?": ("leadership", "improvements"),
            "what measurable impact did your team deliver?": ("leadership", "measurable_impact"),
            "how many projects have you managed simultaneously?": ("leadership", "projects_managed"),
            "what was the average project size in terms of budget or team?": ("leadership", "avg_project_size"),
            "how do you handle project risks and issues?": ("leadership", "risk_management"),
            "have you handled client communication directly?": ("leadership", "client_communication"),
            "how do you track project progress and kpis?": ("leadership", "progress_tracking"),
            "what tools have you used (jira, ms project, etc.)?": ("leadership", "tools_used"),
            "what is your biggest project success story?": ("leadership", "success_story"),
            "have you delivered projects under tight deadlines or constraints?": ("leadership", "tight_deadline_delivery"),
            "what are your primary technical domains?": ("skills", "primary_technical_domains"),
            "what kind of systems have you built (scalable, distributed, cloud)?": ("leadership", "system_types"),
            "which technologies and platforms do you specialize in?": ("leadership", "technology_specializations"),
            "how do you make technical decisions?": ("leadership", "decision_making"),
            "have you reviewed code or set technical standards?": ("leadership", "code_review_standards"),
            "how do you ensure system performance and scalability?": ("leadership", "performance_scalability"),
            "how do you handle technical risks?": ("leadership", "technical_risks"),
            "have you mentored engineers or technical leads?": ("leadership", "mentoring_engineers"),
            "have you handled end-to-end recruitment cycles?": ("leadership", "recruitment_experience"),
            "what is your experience with employee engagement initiatives?": ("leadership", "employee_engagement"),
            "have you worked on performance management systems?": ("leadership", "performance_management"),
            "have you handled conflict resolution or employee relations?": ("leadership", "conflict_resolution"),
            "what hr tools or systems have you used?": ("leadership", "hr_tools"),
            "have you worked on hr policies or compliance?": ("leadership", "policies_compliance"),
            "what hiring volume have you handled?": ("leadership", "hiring_volume"),
            "have you supported leadership or business units directly?": ("leadership", "leadership_support"),
            "what hr transformations or initiatives have you led?": ("leadership", "hr_transformations"),
            "have you handled multiple accounts or programs?": ("leadership", "accounts_programs"),
            "what is your experience in p&l management?": ("leadership", "pnl_management"),
            "how do you ensure delivery excellence across projects?": ("leadership", "delivery_excellence"),
            "have you driven digital transformation or large programs?": ("leadership", "digital_transformation"),
            "how do you manage client relationships at leadership level?": ("leadership", "client_relationships"),
            "how do you handle escalations and crisis situations?": ("leadership", "escalations_crisis"),
            "what governance models have you implemented?": ("leadership", "governance_models"),
            "what business growth or revenue impact have you driven?": ("leadership", "business_impact"),
            "how do you align delivery with business strategy?": ("leadership", "alignment_strategy"),
            # Tech Lead role questions
            "how many engineers have you led, and what were their roles?": ("leadership", "team_scope"),
            "what systems, services, or modules did you own end-to-end?": ("leadership", "technical_ownership"),
            "which key architecture or design decisions did you drive?": ("leadership", "architecture_decisions"),
            "how did you plan sprints and balance delivery with technical debt?": ("leadership", "delivery_planning"),
            "how did you mentor developers and improve team capability?": ("leadership", "mentoring_engineers"),
            # Software Development Senior Specialist questions
            "what is your primary software specialization area?": ("skills", "specialization_area"),
            "can you share an example of a complex technical problem you solved?": ("leadership", "complex_problem_solving"),
            "what engineering practices do you use to ensure code quality and reliability?": ("leadership", "code_quality_practices"),
            "how do you collaborate with architects, product owners, and qa teams?": ("leadership", "cross_team_collaboration"),
            "what measurable technical impact have you delivered in recent projects?": ("leadership", "technical_impact"),
            # Software Development Analyst questions
            "how do you analyze business requirements before implementation?": ("leadership", "requirement_analysis"),
            "what technical documents or artifacts do you usually prepare?": ("leadership", "documentation_approach"),
            "how do you coordinate with business stakeholders and development teams?": ("leadership", "stakeholder_coordination"),
            "how do you handle requirement changes and defect clarifications?": ("leadership", "defect_and_change_management"),
            "what process improvements have you introduced in analysis or delivery?": ("leadership", "process_improvements"),
            # Software Development Manager questions
            "what is the size and structure of the teams you manage?": ("leadership", "org_scope"),
            "how do you manage planning, execution, and release governance?": ("leadership", "delivery_model"),
            "how do you handle hiring, coaching, and performance management?": ("leadership", "people_management"),
            "how do you track risks, dependencies, and cross-team blockers?": ("leadership", "risk_and_dependencies"),
            "what business or customer outcomes did your teams deliver?": ("leadership", "delivery_outcomes"),
            # Business Intelligence Advisor questions
            "which bi tools and platforms do you use most often?": ("skills", "bi_stack"),
            "how do you design kpi dashboards for different business audiences?": ("leadership", "dashboard_strategy"),
            "what is your approach to data modeling and semantic layer design?": ("leadership", "data_modeling"),
            "how do you ensure data quality, consistency, and governance in reports?": ("leadership", "data_governance"),
            "can you share an example where your analytics influenced a key decision?": ("leadership", "decision_impact"),
        }
        self._hydrate_question_bank_mappings()
        self._hydrate_locale_question_aliases()

    def resolve_target(self, question: str) -> tuple[str, str] | None:
        normalized = (question or "").strip().lower()
        if not normalized:
            return None

        target = self._mapping.get(normalized)
        if target:
            return target

        return self._resolve_target_with_llm(normalized)

    def _resolve_target_with_llm(self, normalized_question: str) -> tuple[str, str] | None:
        """
        LLM-assisted fallback for question->(section, field) mapping.

        Uses the known question bank questions as candidates and asks the model
        to select one exact candidate when wording differs.
        """
        if normalized_question in self._llm_question_cache:
            return self._llm_question_cache[normalized_question]

        if not self._llm_service or not self._llm_service.is_enabled():
            self._llm_question_cache[normalized_question] = None
            return None

        candidates = [q for q in sorted(self._mapping.keys()) if q]
        if not candidates:
            self._llm_question_cache[normalized_question] = None
            return None

        # Keep prompt bounded for reliability and cost.
        candidate_list = "\n".join(f"{idx + 1}. {q}" for idx, q in enumerate(candidates[:200]))
        prompt = (
            "Map the INPUT_QUESTION to exactly one candidate question.\n"
            "If no reliable match exists, return index 0.\n"
            "Return strict JSON object with keys: index (int), confidence (0..1).\n\n"
            f"INPUT_QUESTION: {normalized_question}\n\n"
            f"CANDIDATES:\n{candidate_list}"
        )

        raw = self._llm_service.call(
            prompt=prompt,
            system_message=(
                "You are a strict question matching engine for CV questionnaire prompts. "
                "Never invent candidates. Choose only from the list."
            ),
            temperature=0.0,
            max_tokens=120,
            json_mode=True,
        )

        if not raw:
            self._llm_question_cache[normalized_question] = None
            return None

        try:
            parsed = json.loads(raw)
            index = int(parsed.get("index", 0) or 0)
            confidence = float(parsed.get("confidence", 0.0) or 0.0)
        except Exception:
            self._llm_question_cache[normalized_question] = None
            return None

        if index <= 0 or index > min(len(candidates), 200) or confidence < 0.7:
            self._llm_question_cache[normalized_question] = None
            return None

        matched_question = candidates[index - 1]
        target = self._mapping.get(matched_question)
        self._llm_question_cache[normalized_question] = target
        return target

    def _hydrate_question_bank_mappings(self) -> None:
        """Load direct question -> (section, field) mappings from question_bank.yaml."""
        try:
            root = Path(__file__).resolve().parents[3]
            question_bank_path = root / "config" / "questionnaire" / "question_bank.yaml"
            if not question_bank_path.exists():
                return

            with question_bank_path.open("r", encoding="utf-8") as f:
                question_bank = yaml.safe_load(f) or {}

            for section_items in question_bank.values():
                if not isinstance(section_items, list):
                    continue
                for item in section_items:
                    if not isinstance(item, dict):
                        continue

                    qid = str(item.get("id") or "").strip()
                    question_text = str(item.get("question") or "").strip().lower()
                    section = str(item.get("section") or "").strip()
                    field = str(item.get("field") or "").strip()

                    if not question_text or not section or not field:
                        continue

                    target = (section, field)
                    self._mapping[question_text] = target
                    if qid:
                        self._id_to_target[qid] = target
        except Exception:
            # Question bank hydration is best-effort; explicit fallback mappings remain.
            return

    def _hydrate_locale_question_aliases(self) -> None:
        try:
            root = Path(__file__).resolve().parents[3]
            question_bank_path = root / "config" / "questionnaire" / "question_bank.yaml"
            locales_dir = root / "config" / "questionnaire" / "locales"

            if not question_bank_path.exists() or not locales_dir.exists():
                return

            with question_bank_path.open("r", encoding="utf-8") as f:
                question_bank = yaml.safe_load(f) or {}

            if not self._id_to_target:
                for section_items in question_bank.values():
                    if not isinstance(section_items, list):
                        continue
                    for item in section_items:
                        if not isinstance(item, dict):
                            continue
                        qid = str(item.get("id") or "").strip()
                        source_question = str(item.get("question") or "").strip().lower()
                        if not qid or not source_question:
                            continue
                        target = self._mapping.get(source_question)
                        if target:
                            self._id_to_target[qid] = target

            for locale_file in locales_dir.glob("*.yaml"):
                with locale_file.open("r", encoding="utf-8") as f:
                    locale_payload = yaml.safe_load(f) or {}
                localized_questions = locale_payload.get("questions", {})
                if not isinstance(localized_questions, dict):
                    continue

                for qid, localized_question in localized_questions.items():
                    target = self._id_to_target.get(str(qid))
                    if not target:
                        continue
                    normalized = str(localized_question or "").strip().lower()
                    if normalized and normalized not in self._mapping:
                        self._mapping[normalized] = target
        except Exception:
            # Locale alias hydration is best-effort. Base English mapping remains authoritative.
            return

    def apply_answer(self, cv_data: Dict[str, Any], question: str, answer: str) -> Dict[str, Any]:
        print(f"DEBUG MAPPER: apply_answer called with question='{question}', answer='{answer[:100]}...'")
        normalized = question.strip().lower()
        print(f"DEBUG MAPPER: normalized question='{normalized}'")

        target = self.resolve_target(normalized)

        # For explicit questionnaire prompts, always prefer deterministic field mapping.
        # Free-form conversational extraction is reserved for unmapped questions only.
        if target:
            print(f"DEBUG MAPPER: Using direct mapping for known questionnaire prompt")
        else:
            print(f"DEBUG MAPPER: About to check if conversational input for unmapped prompt")
            if self._is_conversational_input(answer):
                print(f"DEBUG MAPPER: Using conversational extractor for comprehensive input")
                extracted_data = extract_from_conversational_text(answer)
                merge_service = MergeCVService()
                merged_data = merge_service.merge(cv_data, extracted_data)
                return merged_data
            print(f"DEBUG MAPPER: NOT detected as conversational input, storing as unmapped answer")

        if not target:
            cv_data.setdefault("unmapped_answers", {})[question] = answer
            return cv_data

        section, field = target
        cv_data.setdefault(section, {})

        if section == "skills" and field in {"primary_skills", "secondary_skills", "tools_and_platforms", "domain_expertise"}:
            parsed = self._parse_list(answer)
            existing = cv_data[section].get(field, [])
            if isinstance(existing, list):
                merged = list(existing)
                for item in parsed:
                    if item and item not in merged:
                        merged.append(item)
                cv_data[section][field] = merged
            else:
                cv_data[section][field] = parsed
            return cv_data

        if section == "personal_details" and field == "total_experience":
            cv_data[section][field] = self._parse_float(answer)
            return cv_data

        if section == "certifications" and field == "certifications":
            cv_data[section] = self._parse_list(answer)
            return cv_data

        if section == "languages" and field == "languages":
            cv_data[section] = self._parse_list(answer)
            return cv_data

        if section == "education" and field == "education":
            cv_data[section] = self._parse_education(answer)
            return cv_data

        if section == "leadership":
            cv_data[section].setdefault(field, [])
            if answer and answer.strip():
                cv_data[section][field].append(answer.strip())
            return cv_data

        cv_data[section][field] = answer.strip()
        return cv_data

    @staticmethod
    def _parse_list(value: str) -> List[str]:
        normalized = value.replace("\r", " ").replace("\n", ", ")
        normalized = re.sub(r"\s+and\s+", ", ", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"[;/]+", ", ", normalized)
        normalized = re.sub(r"\s+\|\s+", ", ", normalized)
        normalized = re.sub(r"\s+-\s+", ", ", normalized)
        normalized = re.sub(r"\s+&\s+", ", ", normalized)
        normalized = re.sub(
            r'^(my\s+)?(primary|secondary|supporting|key|core)?\s*(skill|skills|technology|technologies|tool|tools|platform|platforms|frameworks|framework)\s*(is|are|include|includes|:)?\s*',
            '',
            normalized,
            flags=re.IGNORECASE,
        )
        return [item.strip().rstrip('.') for item in normalized.split(",") if item.strip()]

    @staticmethod
    def _parse_float(value: str):
        try:
            return float(value.strip())
        except Exception:
            return value.strip()

    @staticmethod
    def _parse_education(value: str) -> List[Dict[str, Any]]:
        if not value or not value.strip():
            return []

        text = value.strip()
        # Normalize delimiters and split on clear education boundaries
        text = re.sub(r"\r?\n+", " ", text)
        parts = [part.strip() for part in re.split(
            r'(?=(?:Next,|Then|I have completed intermediate|My secondary school))',
            text,
            flags=re.IGNORECASE,
        ) if part.strip()]

        education = []
        for part in parts:
            qualification = ""
            specialization = ""
            college = ""
            university = ""
            year = ""
            percentage = ""

            # Degree or qualification
            degree_match = re.search(r"(Master(?: of [A-Za-z ]+)?|Bachelor(?: of [A-Za-z ]+)?|B\.?Sc\.?|B\.?Tech\.?|M\.?C\.?A\.?|MBA|Bachelors?|Masters?)", part, re.IGNORECASE)
            if degree_match:
                qualification = degree_match.group(0).strip()

            branch_match = re.search(r"branch is ([^.,]+)", part, re.IGNORECASE)
            if branch_match:
                specialization = branch_match.group(1).strip()

            college_match = re.search(r"college (?:name )?(?:is )?([^.,]+)", part, re.IGNORECASE)
            if college_match:
                college = college_match.group(1).strip()

            university_match = re.search(r"university (?:name )?(?:is )?([^.,]+)", part, re.IGNORECASE)
            if university_match:
                university = university_match.group(1).strip()

            year_match = re.search(r"(20\d{2}|19\d{2})", part)
            if year_match:
                year = year_match.group(0)

            percentage_match = re.search(r"(\d{1,3}(?:\.\d+)?\s*(?:%|percent|percentage))", part, re.IGNORECASE)
            if percentage_match:
                percentage = percentage_match.group(1).strip()

            if not qualification:
                # Identify common education phrases for string fallback
                qual_fallback_match = re.search(r"(\d+(?:th|st|nd|rd) standard|Bachelor of Science|Master of Computer Applications|Master in [^.,]+)", part, re.IGNORECASE)
                if qual_fallback_match:
                    qualification = qual_fallback_match.group(0).strip()

            if not qualification and part:
                qualification = part.strip()

            education.append({
                "qualification": qualification,
                "specialization": specialization,
                "college": college,
                "university": university,
                "year": year,
                "percentage": percentage,
            })

        return education
    
    @staticmethod
    def _is_conversational_input(text: str) -> bool:
        """
        Detect if the input is comprehensive conversational text rather than a simple answer
        """
        text_lower = text.lower()
        
        # Look for multiple personal details indicators in a single message
        indicators = [
            "my name is",
            "phone number is",
            "portal id is",
            "employee id is", 
            "located in",
            "work at",
            "current organization",
            "years of experience",
            "primary skills include",
            "secondary skills",
            "bachelor",
            "master",
            "university",
            "degree",
            "graduated",
            "my email",
            "contact number"
        ]
        
        # Count how many different types of information are mentioned
        indicator_count = sum(1 for indicator in indicators if indicator in text_lower)
        
        # Debug logging
        print(f"DEBUG: Conversational detection for text: {text[:100]}...")
        print(f"DEBUG: Found {indicator_count} indicators")
        print(f"DEBUG: Text length: {len(text)}")
        
        # If multiple indicators (3+) are present, treat as conversational input
        # Also check for length - comprehensive input is typically longer
        is_conversational = indicator_count >= 3 or (indicator_count >= 2 and len(text) > 200)
        print(f"DEBUG: Is conversational: {is_conversational}")
        
        return is_conversational
