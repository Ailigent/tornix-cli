from __future__ import annotations

import json
import mimetypes
import os
import uuid
from pathlib import Path

import click
import httpx

from ._helpers import client, show


@click.group(name="file", help="File upload to the File Center (presigned S3 + sync).")
def file_group() -> None:
    pass


@file_group.command("upload", help="Upload a local file to a project's File Center.")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--project", "project_id", required=True, help="Project id to attach the file to.")
@click.option("--task", "task_id", default=None, help="Task id to attach the file to (stored in document metadata).")
@click.option("--name", default=None, help="Display name (default: the local file name).")
@click.option("--folder", default=None, help="Optional folder/prefix inside the bucket (default: 'files').")
@click.option("--bucket", default="files", help="Storage bucket (default: files).")
@click.option("--context", default=None, help="contextName for the sync (default: project name).")
@click.pass_obj
def file_upload(obj, path, project_id, task_id, name, folder, bucket, context):
    """Upload PATH to S3 via a presigned URL, then sync it into the project's
    File Center (documents). Combines `storage upload` + PUT + `documents sync`
    into one step. Pass --task to attach the file to a task (stored in the
    document's metadata, which is how the frontend renders task attachments)."""
    c = client(obj)
    p = Path(path)
    display_name = name or p.name
    file_size_mb = round(p.stat().st_size / (1024 * 1024), 3)
    content_type = mimetypes.guess_type(p.name)[0] or "application/octet-stream"

    # 1. Get a presigned upload URL
    prefix = (folder or "files").strip("/")
    storage_path = f"{prefix}/{project_id}/{uuid.uuid4()}{p.suffix.lower()}"
    try:
        presigned = c.post(
            "/api/v1/storage/upload",
            json={"bucket": bucket, "path": storage_path, "contentType": content_type},
        )
    except Exception as e:
        raise click.UsageError(f"failed to get presigned URL: {e}")
    upload_url = presigned.get("upload_url") if isinstance(presigned, dict) else None
    if not upload_url:
        raise click.UsageError(f"no upload_url in response: {presigned}")

    # 2. PUT the file body straight to S3
    with open(p, "rb") as fh:
        data = fh.read()
    try:
        resp = httpx.put(upload_url, content=data, headers={"Content-Type": content_type}, timeout=300)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise click.UsageError(f"S3 upload failed: {e}")

    # 3. Sync into the File Center (documents) for the project
    metadata = {"synced_from": "general", "storage_bucket": bucket}
    if task_id:
        metadata["task_id"] = task_id
        metadata["original_file_type"] = content_type
    sync_body = {
        "fileName": display_name,
        "filePath": storage_path,
        "fileSizeMb": file_size_mb,
        "mimeType": content_type,
        "source": "general",
        "contextName": context or "File Center",
        "projectId": project_id,
        "storageBucket": bucket,
        "metadata": metadata,
    }
    try:
        synced = c.post("/api/v1/documents/sync", json=sync_body)
    except Exception as e:
        raise click.UsageError(f"file uploaded but sync failed: {e}")

    result = {
        "uploaded": True,
        "document_id": synced.get("document_id") if isinstance(synced, dict) else None,
        "name": display_name,
        "path": storage_path,
        "size_mb": file_size_mb,
        "project_id": project_id,
    }
    if task_id:
        result["task_id"] = task_id
    show(obj, result)
