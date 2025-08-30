# Storage (app/storage)

This document explains how the `app/storage` folder is used and how to persist uploaded files in development and production.

Summary

- `app/storage` holds runtime-uploaded files (images, etc.). These files are application data, not source code, and must not be committed to Git. Keep `app/storage/` in `.gitignore`.

Development (recommended)

- Use the provided `docker-compose.dev.yml` which mounts the host folder `./app/storage` into the container. Files uploaded by the app are stored on your host and persist after the container stops or is recreated:

```powershell
cd D:\Proyectos\Z\ac_store\ac9_sport_api
docker compose -f docker-compose.dev.yml up --build
```

- Stopping `docker compose` (Ctrl+C or `docker compose down`) does NOT mutate the `Dockerfile`. It simply stops/removes containers. If you used a host-mounted folder (as above), files remain on your host in `ac9_sport_api\app\storage`.
- If you DID NOT mount a host folder (i.e. you ran a container without `-v ./app/storage:...`), uploaded files are inside the container's writable layer. They will be removed if you `docker rm` the container. You can recover them before removal with `docker cp`.

Production

- Don't mount host paths from ephemeral hosts. Use one of:
  - Managed block/storage volumes attached to the host (depends on your provider).
  - Object storage: S3, GCS, Azure Blob (recommended for scale and durability).

Recommendations

- Keep `app/storage/` in `.gitignore`.
- Use `docker-compose.dev.yml` for local development to persist and inspect uploads.
- For production, store files in object storage and serve them via CDN. If you must use local disk in production, mount a managed persistent volume (not a host path in autoscaled environments).

Quick troubleshooting

- Files created inside container but not mounted? Copy them out before removing the container:

```powershell
# list containers
docker ps -a
# copy file from container to host
docker cp <containerId>:/app/app/storage/<filename> D:\some\host\path\
```

- To snapshot a container's filesystem into an image (not recommended for uploads):

```powershell
docker commit <containerId> ac9_sport_api:snapshot
```

If you want, I can add an optional small script to sync `app/storage` to an S3 bucket for backups or to configure direct S3 uploads from the API.
