import os,sys,json,tempfile,shutil,time,subprocess
from pathlib import Path
from llama_cpp import Llama
sys.path.insert(0,os.path.abspath('p'))
from tokenfrugal.providers import _parse_action
from tokenfrugal.agent import Agent
from tokenfrugal.audit import AuditLog
from tokenfrugal.budget import Budget
from tokenfrugal.policy import Policy
from tokenfrugal.tools import ToolBox
llm=Llama(model_path='model.gguf',n_ctx=8192,n_threads=1,n_threads_batch=1,verbose=False,seed=42)
class LocalProvider:
 name='qwen2.5-coder-1.5b-instruct-q4_k_m-local'
 def __init__(self): self.last_usage=0; self.rows=[]
 def act(self,messages,max_tokens=512):
  st=time.time();d=llm.create_chat_completion(messages=messages,max_tokens=max_tokens,temperature=0,response_format={'type':'json_object'})
  self.last_usage=d['usage']['total_tokens'];text=d['choices'][0]['message']['content']
  self.rows.append({'usage':d['usage'],'seconds':round(time.time()-st,3),'reply':text})
  print('MODEL',json.dumps(self.rows[-1]),flush=True);return _parse_action(text)
 def usage(self,messages,reply): return self.last_usage
work=tempfile.mkdtemp(prefix='tf-live-');repo=os.path.join(work,'repo');shutil.copytree('p/demo/sample_repo',repo)
audit=AuditLog('out/live-audit.jsonl');provider=LocalProvider();agent=Agent(provider,ToolBox(Policy(repo),audit),Budget(40000),audit,repo,max_steps=10)
result=agent.run('Fix the inventory calculation bug. Verify with python3 -m unittest discover -s tests -q. Do not modify tests. Read inventory/total.py and tests to identify the cause.')
check=subprocess.run(['python3','-m','unittest','discover','-s','tests','-q'],cwd=repo,capture_output=True,text=True)
summary={'model':provider.name,'result':result,'independent_tests_exit':check.returncode,'independent_test_output':check.stdout+check.stderr,'calls':provider.rows,'total_actual_tokens':sum(r['usage']['total_tokens'] for r in provider.rows),'transcript':agent.transcript,'temperature':0,'seed':42,'network_during_inference':False,'scope':'Single tiny fixture, not a competitive benchmark or general success claim.'}
Path('out/live-result.json').write_text(json.dumps(summary,indent=2));print('RESULT',json.dumps(summary),flush=True)
