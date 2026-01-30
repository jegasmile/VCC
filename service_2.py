from fastapi import FastAPI

app = FastAPI()

@app.get("/process")
def process():
    return {"message": "Helle, This is JegadeeshKumar(M25AI2106)"}
