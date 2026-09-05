from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routes import router
from api.security import FileTooLargeError, InvalidFileTypeError
from db.database import init_db
from extractors.epub_extractor import EpubParsingError
from extractors.pdf_extractor import PdfParsingError
from extractors.zip_safety import ZipSafetyError
from reconstructors.epub_reconstructor import EpubReconstructionError
from reconstructors.pdf_reconstructor import PdfReconstructionError
from translator.llm_client import TranslationError

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="traductor-docs", lifespan=lifespan)


@app.exception_handler(FileTooLargeError)
async def file_too_large_handler(request: Request, exc: FileTooLargeError):
    return JSONResponse(status_code=413, content={"detail": str(exc)})


@app.exception_handler(InvalidFileTypeError)
async def invalid_file_type_handler(request: Request, exc: InvalidFileTypeError):
    return JSONResponse(status_code=415, content={"detail": str(exc)})


@app.exception_handler(TranslationError)
async def translation_error_handler(request: Request, exc: TranslationError):
    # Under the job model (Fase 5) this no longer fires for /translate-*:
    # translate_document() now only runs inside the background job runner
    # (routes._run_job), which catches TranslationError itself and marks
    # the job 'failed' instead of raising into a response. Kept registered
    # for any direct/synchronous caller of translate_document. Still no
    # partial saves either way — a failing chunk fails the whole document.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(EpubParsingError)
async def epub_parsing_error_handler(request: Request, exc: EpubParsingError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ZipSafetyError)
async def zip_safety_error_handler(request: Request, exc: ZipSafetyError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(PdfParsingError)
async def pdf_parsing_error_handler(request: Request, exc: PdfParsingError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(EpubReconstructionError)
async def epub_reconstruction_error_handler(request: Request, exc: EpubReconstructionError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(PdfReconstructionError)
async def pdf_reconstruction_error_handler(request: Request, exc: PdfReconstructionError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(router)
