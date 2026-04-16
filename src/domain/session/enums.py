from enum import Enum


class SessionStatus(str, Enum):
	"""Lifecycle status for persisted CV sessions."""

	ACTIVE = "active"
	EXPORTED = "exported"
	EXPIRED = "expired"
	DELETED = "deleted"


class SessionSourceType(str, Enum):
	"""Input and workflow channels that can mutate session state."""

	BOT_CONVERSATION = "bot_conversation"
	AUDIO_UPLOAD = "audio_upload"
	LIVE_VOICE_RECORDING = "live_voice_recording"
	DOCUMENT_UPLOAD = "document_upload"
	MANUAL_EDIT = "manual_edit"
	EXPORT_DOCX = "export_docx"
	EXPORT_PDF = "export_pdf"
