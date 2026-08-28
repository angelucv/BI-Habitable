# Gunicorn — CPEH Fase II ROJO
import multiprocessing

bind = "127.0.0.1:8000"
workers = min(4, multiprocessing.cpu_count() * 2 + 1)
timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
capture_output = True
