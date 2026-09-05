from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routes import router
from api.security import FileTooLargeError, InvalidFileTypeError
from translator.llm_client import TranslationError

load_dotenv()

app = FastAPI(title="traductor-docs")


@app.exception_handler(FileTooLargeError)
async def file_too_large_handler(request: Request, exc: FileTooLargeError):
    return JSONResponse(status_code=413, content={"detail": str(exc)})


@app.exception_handler(InvalidFileTypeError)
async def invalid_file_type_handler(request: Request, exc: InvalidFileTypeError):
    return JSONResponse(status_code=415, content={"detail": str(exc)})


@app.exception_handler(TranslationError)
async def translation_error_handler(request: Request, exc: TranslationError):
    # Aborts the whole request on first failure — no partial saves, no
    # retries. Revisit this once large documents (EPUB/PDF) make discarding
    # all progress on a late failure too costly.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(router)
