"""Filesystem browsing API for path selection."""
import logging
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


class DirectoryItem(BaseModel):
    """Directory item information."""
    name: str
    path: str
    is_directory: bool
    is_readable: bool


class DirectoryListingResponse(BaseModel):
    """Directory listing response."""
    current_path: str
    parent_path: Optional[str] = None
    items: List[DirectoryItem]


@router.get("/browse", response_model=DirectoryListingResponse)
async def browse_directory(path: str = "/"):
    """Browse filesystem directory."""
    try:
        path = os.path.abspath(path)

        if not os.path.exists(path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Path does not exist: {path}"
            )

        if not os.path.isdir(path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a directory: {path}"
            )

        parent_path = os.path.dirname(path) if path != "/" else None

        items = []
        try:
            entries = os.listdir(path)
            entries.sort()

            for entry in entries:
                entry_path = os.path.join(path, entry)

                try:
                    is_dir = os.path.isdir(entry_path)
                    is_readable = os.access(entry_path, os.R_OK)

                    if is_dir:
                        items.append(DirectoryItem(
                            name=entry,
                            path=entry_path,
                            is_directory=True,
                            is_readable=is_readable
                        ))
                except (PermissionError, OSError) as e:
                    logger.debug(f"Cannot access {entry_path}: {e}")
                    continue

        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {path}"
            )

        return DirectoryListingResponse(
            current_path=path,
            parent_path=parent_path,
            items=items
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing directory {path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error browsing directory: {str(e)}"
        )


@router.get("/common-paths", response_model=List[DirectoryItem])
async def get_common_paths():
    """Get list of common starting paths."""
    common_paths = ["/", "/home", "/media", "/mnt", "/opt", "/srv", "/var", "/tmp"]

    items = []
    for path in common_paths:
        if os.path.exists(path) and os.path.isdir(path):
            try:
                is_readable = os.access(path, os.R_OK)
                items.append(DirectoryItem(
                    name=path,
                    path=path,
                    is_directory=True,
                    is_readable=is_readable
                ))
            except (PermissionError, OSError):
                continue

    return items

