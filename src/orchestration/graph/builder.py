from src.orchestration.graph.nodes import WorkflowNodes


class WorkflowGraphBuilder:
    def build_definition(self) -> dict:
        return {
            "nodes": [
                WorkflowNodes.START,
                WorkflowNodes.DETECT_ROLE,
                WorkflowNodes.ASK_QUESTION,
                WorkflowNodes.ANALYZE_ANSWER,
                WorkflowNodes.RETRIEVE_CONTEXT,
                WorkflowNodes.ENHANCE_CONTENT,
                WorkflowNodes.VALIDATE,
                WorkflowNodes.FOLLOWUP,
                WorkflowNodes.PREVIEW,
                WorkflowNodes.END,
            ],
            "edges": [
                (WorkflowNodes.START, WorkflowNodes.DETECT_ROLE),
                (WorkflowNodes.DETECT_ROLE, WorkflowNodes.ASK_QUESTION),
                (WorkflowNodes.ASK_QUESTION, WorkflowNodes.ANALYZE_ANSWER),
                (WorkflowNodes.ANALYZE_ANSWER, WorkflowNodes.RETRIEVE_CONTEXT),
                (WorkflowNodes.RETRIEVE_CONTEXT, WorkflowNodes.ENHANCE_CONTENT),
                (WorkflowNodes.ENHANCE_CONTENT, WorkflowNodes.VALIDATE),
                (WorkflowNodes.VALIDATE, WorkflowNodes.FOLLOWUP),
                (WorkflowNodes.FOLLOWUP, WorkflowNodes.PREVIEW),
                (WorkflowNodes.PREVIEW, WorkflowNodes.END),
            ],
        }
