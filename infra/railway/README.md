# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_APPLICATION_KEY_ID` | Your B2 application key ID |
| `B2_APPLICATION_KEY` | Your B2 application key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_REGION` | Your bucket's region (e.g. `us-west-004`) |
| `FP_DB_HOST` / `FP_DB_PORT` / `FP_DB_USER` / `FP_DB_PASSWORD` / `FP_DB_NAME` | Managed MySQL connection for the Dejavu fingerprint index |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |

> The API needs a reachable MySQL (Dejavu's fingerprint backend) and `ffmpeg`
> installed for MP3 decode. On Railway, add a MySQL plugin/service and point the
> `FP_DB_*` vars at it. The S3 endpoint is derived from `B2_REGION`
> (`https://s3.<B2_REGION>.backblazeb2.com`).

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
