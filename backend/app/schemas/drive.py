from pydantic import BaseModel


class DriveFile(BaseModel):
    file_id: str
    name: str
    mime_type: str
    modified_time: str | None
    web_view_link: str | None


class DriveFileContent(BaseModel):
    file_id: str
    name: str
    content: str
    truncated: bool
