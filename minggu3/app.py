from http.server import BaseHTTPRequestHandler, HTTPServer 
import json 
import os 
import psycopg
 
def database_status():    
    try:        
        with psycopg.connect(            
            host=os.getenv("DB_HOST", "db"),            
            port=os.getenv("DB_PORT", "5432"),            
            dbname=os.getenv("DB_NAME", "db-latihan"),            
            user=os.getenv("DB_USER", "user-1"),            
            password=os.getenv("DB_PASSWORD", "123"),        
        ) as conn:            
            with conn.cursor() as cur:                
                cur.execute("SELECT 1")                
                return cur.fetchone()[0] == 1    
    except Exception:        
        return False 
    
class Handler(BaseHTTPRequestHandler):    
    def do_GET(self):        
        if self.path == "/health":            
            ok = database_status()            
            data = {"app": "ok", "database": "ok" if ok else "error"}            
            self.send_response(200 if ok else 503)        
        else:            
            data = {"error": "not found"}            
            self.send_response(404)        
            
        self.send_header("Content-Type", "application/json")        
        self.end_headers()        
        self.wfile.write(json.dumps(data).encode()) 
        
HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()