from fastapi import FastAPI
app = FastAPI(title="Real Estate OS API")
@app.get("/")
def read_root():
    return {"message": "Real Estate OS API is running."}
