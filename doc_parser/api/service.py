"""
FastAPI Service Module
Provides HTTP API interface
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from typing import List, Optional
import tempfile
import shutil
import json
import os

from .client import DocumentParserClient


app = FastAPI(
    title="OCR and Structured Extraction API",
    description="Intelligent document recognition and structured extraction tool HTTP API service",
    version="1.0.0"
)

# Global client instance
client = DocumentParserClient()


@app.post("/process/file", summary="Process single file")
async def process_file(
    file: UploadFile = File(...),
    config: Optional[str] = Form(None, description="JSON configuration string")
):
    """
    Process uploaded file

    - **file**: Image or PDF file to process
    - **config**: Optional JSON configuration string to override defaults
    """
    # Validate file type
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")

    # Save temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    try:
        # Update config (if provided)
        if config:
            try:
                config_dict = json.loads(config)
                client.update_config(**config_dict)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON configuration")

        # Process file
        result = client.process_file(temp_path)
        return JSONResponse(content=result)

    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass


@app.post("/process/files", summary="Batch process files")
async def process_files(
    files: List[UploadFile] = File(...),
    config: Optional[str] = Form(None, description="JSON configuration string")
):
    """
    Batch process uploaded files

    - **files**: List of image or PDF files to process
    - **config**: Optional JSON configuration string
    """
    temp_paths = []

    try:
        # Save all temporary files
        for file in files:
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in {'.jpg', '.jpeg', '.png', '.pdf'}:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")

            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                shutil.copyfileobj(file.file, temp_file)
                temp_paths.append(temp_file.name)

        # Update config
        if config:
            try:
                config_dict = json.loads(config)
                client.update_config(**config_dict)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON configuration")

        # Batch process
        results = client.process_files(temp_paths)
        return JSONResponse(content={"results": results})

    finally:
        # Clean up temporary files
        for path in temp_paths:
            try:
                os.unlink(path)
            except:
                pass


@app.post("/extract/text", summary="Extract text only")
async def extract_text(file: UploadFile = File(...)):
    """
    Extract text from file without structuring

    - **file**: Image or PDF file to process
    """
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in {'.jpg', '.jpeg', '.png', '.pdf'}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    try:
        text = client.extract_text(temp_path)
        return JSONResponse(content={"text": text})
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


@app.get("/config", summary="Get current configuration")
async def get_config():
    """Get current configuration"""
    return JSONResponse(content={
        "ocr": client.processor.config.ocr.dict(),
        "extraction": client.processor.config.extraction.dict(),
        "validation": client.processor.config.validation.dict()
    })


@app.put("/config", summary="Update configuration")
async def update_config(config_data: dict):
    """
    Update client configuration

    - **config_data**: Configuration dictionary containing ocr, extraction, and validation fields
    """
    try:
        client.update_config(**config_data)
        return {"message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Configuration update failed: {str(e)}")


@app.get("/health", summary="Health check")
async def health_check():
    """Service health check"""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
