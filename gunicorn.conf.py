import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "50"))
max_requests = 500
max_requests_jitter = 50
timeout = 30
keepalive = 15
graceful_timeout = 5
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "error"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
disable_redirect_access_to_syslog = True
capture_output = True
enable_stdio_inheritance = True 