import os
import secrets
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from .evidence import embed
from .retrieval import embedding_version
from .sandbox import isolated_process
from .diagnostics import diagnose
app=FastAPI(title='BenchTrace engineering engine',version='0.1.0')

def authorize(authorization: str=Header(default='')):
    token=os.environ.get('ENGINE_TOKEN','')
    if not token or not secrets.compare_digest(authorization,'Bearer '+token): raise HTTPException(401,'Unauthorized')

class ProcessRequest(BaseModel):
    storage_key: str=Field(pattern=r'^[a-f0-9-]{36}\.[a-z_]+$',max_length=60)
    options: dict=Field(default_factory=dict)
class DiagnosticRequest(BaseModel):
    problem:str=Field(default="",max_length=10000)
    files:list[dict]=Field(max_length=200)
    tests:list[dict]=Field(default_factory=list,max_length=1000)
class EmbedRequest(BaseModel):
    text:str=Field(max_length=20000)

@app.get('/health')
def health():return {'status':'ok'}
@app.post('/process',dependencies=[Depends(authorize)])
def analyze(request:ProcessRequest):
    try:return isolated_process(Path('/uploads')/request.storage_key,request.options)
    except (ValueError,UnicodeError,OSError,KeyError) as e:raise HTTPException(422,str(e)[:500]) from e
@app.post('/diagnose',dependencies=[Depends(authorize)])
def diagnostic(request:DiagnosticRequest):return diagnose(request.files,request.tests,request.problem)
@app.post('/embed',dependencies=[Depends(authorize)])
def embedding(request:EmbedRequest):return {'embedding':embed(request.text),'method':os.getenv('EMBEDDING_MODE','semantic'),'version':embedding_version()}

class AnswerRequest(BaseModel):
    question:str=Field(max_length=2000)
    evidence:list[dict]=Field(max_length=6)
@app.post('/answer',dependencies=[Depends(authorize)])
def generate_answer(request:AnswerRequest):
    from .answers import answer
    return answer(request.question,request.evidence)
@app.post('/provider/test',dependencies=[Depends(authorize)])
def provider_test():
    from .answers import provider_connection_check
    return provider_connection_check()
@app.post('/config',dependencies=[Depends(authorize)])
def config():return {'embedding_version':embedding_version(),'embedding_mode':os.getenv('EMBEDDING_MODE','semantic'),'model':'BAAI/bge-small-en-v1.5','provider_configured':bool(os.getenv('LLM_BASE_URL')),'diagnostics':'deterministic evidence rules','decoder_defaults':{'threshold':1.65,'baud':115200,'cpol':0,'cpha':0}}

class CompareRequest(BaseModel):
    left:str=Field(pattern=r'^[a-f0-9-]{36}\.csv$')
    right:str=Field(pattern=r'^[a-f0-9-]{36}\.csv$')
    channel:str=Field(max_length=100)
@app.post('/compare',dependencies=[Depends(authorize)])
def compare(request:CompareRequest):
    from .signals import compare_csv
    try:return compare_csv((Path('/uploads')/request.left).read_text(),(Path('/uploads')/request.right).read_text(),request.channel)
    except (ValueError,OSError) as e:raise HTTPException(422,str(e)) from e
