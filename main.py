from fastapi import FastAPI

from routers import auth, tasks

app = FastAPI(title="TaskFlow")

app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/")
async def root():
    return {"message": "TaskFlow is alive"}