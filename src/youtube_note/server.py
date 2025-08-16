import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from youtube_transcript_api import YouTubeTranscriptApi, FetchedTranscript
import re
from langchain.chat_models import init_chat_model
from langchain.prompts import ChatPromptTemplate
import os
import dotenv

from .storage import get_db
from .model import YouTubeNote

dotenv.load_dotenv()

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_video_id(youtube_url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract video ID from URL: {youtube_url}")

class TranscriptRequest(BaseModel):
    youtube_url: str

class TranscriptResponse(BaseModel):
    transcript: str

class SummaryRequest(BaseModel):
    transcript: str

class SummaryResponse(BaseModel):
    summary: str

class NoteRequest(BaseModel):
    summary: str

class NoteResponse(BaseModel):
    note: str

class TranscriptItem(BaseModel):
    id: int
    youtube_url: str
    transcript: str

yt_client = YouTubeTranscriptApi()
llm = init_chat_model(
    model_provider="openai",
    model="gpt-5-chat",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("openrouter_api_key"),
)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that summarizes transcripts of YouTube videos. Your response are to be rendered in a Youtube Note Manager application, so skip preamble and followup question, just the main content itself. Use Markdown format. Write in an easy to read and digest manner. Prioritize readability over succinctness."),
    ("user", "{transcript}")
])
class ChainWrapper:
    def __init__(self, runnable):
        self._runnable = runnable

    def invoke(self, *args, **kwargs):
        return self._runnable.invoke(*args, **kwargs)

chain = ChainWrapper(prompt | llm)

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.post("/transcript", response_class=HTMLResponse)
async def get_transcript(request: Request, request_data: TranscriptRequest):
    try:
        video_id = extract_video_id(request_data.youtube_url)
        transcript_list: FetchedTranscript = yt_client.fetch(video_id=video_id)
        transcript = "\n".join([f"[{int(item.start)//60:02d}:{int(item.start)%60:02d}] {item.text}"  for item in transcript_list])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to get transcript")
        error_msg = f"Failed to get transcript: {str(e)}"
        if "Could not retrieve a transcript" in str(e):
            error_msg = "No transcript available for this video. The video might not have captions or transcripts enabled."
        elif "Video unavailable" in str(e):
            error_msg = "Video is unavailable or does not exist."
        raise HTTPException(status_code=400, detail=error_msg)

    with get_db() as db:
        summary_response = chain.invoke({"transcript": transcript})
        summary_text = summary_response.content if hasattr(summary_response, 'content') else str(summary_response)
        try:
            summary_text = re.sub(r"[ \t]+\n", "\n", summary_text)
            summary_text = re.sub(r"\n{3,}", "\n\n", summary_text).strip()
        except Exception:
            pass

        def extract_title_from_summary(text: str) -> str:
            try:
                cleaned = text.lstrip("#- *\n\t").strip()
                first_line = cleaned.splitlines()[0] if cleaned else ""
                import re as _re
                m = _re.search(r"([^.?!\n]+[.?!])", first_line)
                candidate = m.group(1) if m else first_line
                candidate = candidate.strip().strip('#').strip('-').strip('*').strip()
                return candidate[:200] if candidate else "Untitled"
            except Exception:
                return "Untitled"

        title_text = extract_title_from_summary(summary_text)

        new_note = YouTubeNote(
            youtube_url=request_data.youtube_url,
            title=title_text,
            transcript=transcript,
            summary=summary_text,
            note=""
        )

        existing_note = db.query(YouTubeNote).filter(YouTubeNote.youtube_url == request_data.youtube_url).first()
        if existing_note:
            existing_note.transcript = transcript
            existing_note.summary = summary_text
            existing_note.note = ""
            existing_note.title = title_text
        else:
            db.add(new_note)
        db.commit()
        if existing_note:
            db.refresh(existing_note)
            note_obj = existing_note
        else:
            db.refresh(new_note)
            note_obj = new_note

    return templates.TemplateResponse("_note_card.html", {"request": request, "note": note_obj})

@app.post("/summarize", response_model=SummaryResponse)
async def summarize_transcript(request: SummaryRequest):
    summary = "This is a dummy summary of the provided transcript."
    return SummaryResponse(summary=summary)

@app.post("/note", response_model=NoteResponse)
async def write_note(request: NoteRequest):
    note = "This is a dummy note based on the provided summary."
    return NoteResponse(note=note)

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    from .storage import get_db
    from .model import YouTubeNote

    with get_db() as db:
        all_notes = db.query(YouTubeNote).order_by(YouTubeNote.id.desc()).all()

    return templates.TemplateResponse("index.html", {"request": request, "notes": all_notes})


