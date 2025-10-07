Upload reliability hardening - checklist

- [x] Route consistency: frontend uses /api/upload proxy → backend /upload-pdf
- [x] HTTP verb: POST; added OPTIONS handler for preflight
- [x] CORS: FastAPI already allows methods/headers; proxy avoids CORS entirely
- [x] Multipart: python-multipart present in requirements
- [x] Content-Type: do not set manually; forward FormData as-is
- [x] Field name: using 'file' as expected by FastAPI
- [x] Size limit: backend streams to disk and enforces UPLOAD_MAX_MB (default 10)
- [x] Temp dir: writing to backend/uploads via existing path; Docker volume mounted
- [ ] S3/MinIO: optional; not modified here

Smoke tests

Backend direct

API=http://localhost:8000
curl -i -X OPTIONS $API/upload-pdf
curl -i -F "file=@/path/to/sample.pdf" $API/upload-pdf

Frontend proxy

curl -i -X POST -H "Origin: http://localhost:3000" -F "file=@/path/to/sample.pdf" http://localhost:3000/api/upload

Negative

curl -i -F "file=@/path/to/sample.txt" $API/upload-pdf  # 415
curl -i -X GET $API/upload-pdf                           # 405


