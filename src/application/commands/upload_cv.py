import os
from typing import Dict, Any, Optional
from src.infrastructure.parsers.docx_extractor import extract_docx
from src.infrastructure.parsers.doc_extractor import extract_doc
from src.infrastructure.parsers.pdf_extractor import extract_pdf
from src.infrastructure.parsers.resume_parser import ResumeParser
from src.ai.services.cv_workflow_orchestrator import CVWorkflowOrchestrator


class UploadCVCommand:
    """
    CV Upload Command with full workflow support.
    
    Implements the complete CV processing pipeline:
    Upload CV → AI Extraction → Schema Mapping → RAG Enrichment → 
    Validation → Preview → Edit Loop
    """

    def __init__(self, use_workflow: bool = True):
        """
        Initialize upload CV command.
        
        Args:
            use_workflow: If True, use full AI workflow. If False, use basic parser.
        """
        self.use_workflow = use_workflow
        self.orchestrator = None
        self.basic_parser = ResumeParser()
        
        if use_workflow:
            try:
                self.orchestrator = CVWorkflowOrchestrator()
            except Exception as e:
                print(f"Workflow orchestrator unavailable: {e}. Falling back to basic parser.")
                self.use_workflow = False

    def execute(self, file_path: str, workflow_options: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
        """
        Execute CV upload and processing through the complete workflow.
        
        Args:
            file_path: Path to uploaded CV file
            workflow_options: Optional dict to enable/disable specific workflow steps
            
        Returns:
            Complete workflow result with extracted, enriched, and validated CV data
        """
        print(f"\n{'='*60}")
        print(f"[CV] Processing CV: {os.path.basename(file_path)}")
        print(f"{'='*60}\n")
        
        # Step 1: Extract text from file
        try:
            text = self._extract_text_from_file(file_path)
            print(f"[OK] Text extracted: {len(text)} characters\n")
        except Exception as e:
            return {
                "status": "error",
                "error": f"Text extraction failed: {str(e)}",
                "file_path": file_path
            }
        
        # Step 2: Process through workflow
        if self.use_workflow and self.orchestrator:
            try:
                workflow_result = self.orchestrator.process_cv(text, workflow_options)
                workflow_result["file_path"] = file_path
                workflow_result["original_filename"] = os.path.basename(file_path)
                
                # Generate preview if workflow completed successfully
                if workflow_result.get("status") == "completed":
                    preview = self.orchestrator.preview_cv(workflow_result)
                    workflow_result["preview"] = preview
                
                # Clean up the response structure - return clean preview format
                return self._format_response(workflow_result)
                
            except Exception as e:
                print(f"[WARNING] Workflow failed: {e}. Falling back to basic parser.")
                return self._basic_fallback(text, file_path, str(e))
        else:
            # Use basic parser
            return self._basic_fallback(text, file_path)
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text from uploaded CV file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If file format is unsupported
        """
        if file_path.endswith(".docx"):
            return extract_docx(file_path)
        elif file_path.endswith(".doc"):
            return extract_doc(file_path)
        elif file_path.endswith(".pdf"):
            return extract_pdf(file_path)
        else:
            raise ValueError("Unsupported file format. Please use .doc, .docx, or .pdf")
    
    def _basic_fallback(self, text: str, file_path: str, error: Optional[str] = None) -> Dict[str, Any]:
        """
        Fallback to basic parser if workflow fails.
        
        Args:
            text: Extracted text
            file_path: Original file path
            error: Optional error message from workflow
            
        Returns:
            Basic parsing result
        """
        parsed_data = self.basic_parser.parse(text)
        result = {
            "status": "completed",
            "cv_data": parsed_data,
            "extraction_method": "basic",
            "file_path": file_path,
            "original_filename": os.path.basename(file_path),
            "text_length": len(text),
            "steps_completed": ["basic_extraction"]
        }
        
        if error:
            result["workflow_error"] = error
            result["extraction_method"] = "basic (workflow failed)"
        
        return result
    
    def _format_response(self, workflow_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the workflow result into a clean, structured response.
        
        Args:
            workflow_result: Raw workflow result
            
        Returns:
            Cleaned and properly structured response
        """
        # Create clean response structure
        clean_response = {
            "status": workflow_result.get("status"),
            "file_info": {
                "file_path": workflow_result.get("file_path"),
                "original_filename": workflow_result.get("original_filename")
            },
            "extraction": {
                "method": workflow_result.get("metadata", {}).get("extraction_method", "unknown"),
                "steps_completed": workflow_result.get("steps_completed", []),
                "warnings": workflow_result.get("warnings", []),
                "errors": workflow_result.get("errors", [])
            },
            "cv_data": workflow_result.get("cv_data", {}),
            "sections_detected": workflow_result.get("metadata", {}).get("sections_detected", {}),
            "validation": workflow_result.get("validation", {}),
            "suggestions": workflow_result.get("suggestions", {}),
            "preview": workflow_result.get("preview", {})
        }
        
        return clean_response
    
    def apply_user_edits(self, workflow_result: Dict[str, Any], edits: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply user edits to CV data and re-run validation.
        
        Args:
            workflow_result: Original workflow result
            edits: Dictionary of edits to apply
            
        Returns:
            Updated workflow result with edits applied
        """
        if not self.orchestrator:
            return {"error": "Workflow orchestrator not available"}
        
        cv_data = workflow_result.get("cv_data", {})
        edit_result = self.orchestrator.apply_edits(cv_data, edits)
        
        # Update workflow result
        workflow_result["cv_data"] = edit_result["cv_data"]
        workflow_result["validation"]["schema_validation"] = edit_result["validation"]
        workflow_result["validation"]["gaps"] = edit_result["gaps"]
        workflow_result["edit_history"] = workflow_result.get("edit_history", [])
        workflow_result["edit_history"].append({
            "timestamp": "now",  # In production, use actual timestamp
            "sections_edited": list(edits.keys())
        })
        
        # Regenerate preview
        preview = self.orchestrator.preview_cv(workflow_result)
        workflow_result["preview"] = preview
        
        return workflow_result
