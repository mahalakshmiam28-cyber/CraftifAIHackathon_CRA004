"""Minimal demo adapter for PipeGen/DeepStream detection event JSON. Not a model or PipeGen integration."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json, time
EVENTS=[]
class Handler(BaseHTTPRequestHandler):
 def headers(self, status=200):
  self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Access-Control-Allow-Origin','http://localhost:8000');self.send_header('Access-Control-Allow-Headers','Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS');self.end_headers()
 def do_OPTIONS(self):self.headers(204)
 def do_GET(self):
  if self.path!='/api/events':self.headers(404);return
  self.headers();self.wfile.write(json.dumps({'events':EVENTS[-100:]}).encode())
 def do_POST(self):
  if self.path!='/api/events':self.headers(404);return
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>4096:raise ValueError('Payload too large')
   obj=json.loads(self.rfile.read(n));event=obj.get('event');conf=obj.get('confidence')
   if event not in ('fall_detected','fall_cleared','person_detected') or (conf is not None and (not isinstance(conf,(int,float)) or isinstance(conf,bool) or not 0<=conf<=1)):raise ValueError('Invalid event')
   item={'id':len(EVENTS)+1,'time':time.time(),'event':event,'confidence':conf,'source':'external adapter'};EVENTS.append(item);self.headers(201);self.wfile.write(json.dumps(item).encode())
  except (ValueError,TypeError,json.JSONDecodeError) as e:self.headers(400);self.wfile.write(json.dumps({'error':str(e)}).encode())
if __name__=='__main__':
 print('Event adapter at http://localhost:8001');ThreadingHTTPServer(('127.0.0.1',8001),Handler).serve_forever()
