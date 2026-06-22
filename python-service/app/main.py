from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health():
    return {
        "message": "RNGine simulation service is healthy, and up and running. Happy simulating!"
    }
