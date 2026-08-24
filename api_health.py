#!/usr/bin/env python3
"""health-api: minimal JSON API over the health Postgres DB (replaces datasette).
Endpoints:
  GET /daily_metrics?limit=N&from=YYYY-MM-DD&to=YYYY-MM-DD
  GET /spo2_epochs?date=YYYY-MM-DD&limit=N
  GET /latest
  GET /
"""
import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv
load_dotenv('/root/garmin-health/.env')
import db  # noqa: E402

PORT = 8094
ALLOWED = {
    'daily_metrics': ['date', 'hrv_last_night', 'hrv_weekly_avg', 'sleep_score', 'sleep_duration',
                      'sleep_rem', 'resting_hr', 'bb_max', 'bb_min', 'stress_avg', 'stress_max',
                      'steps', 'spo2_min', 'spo2_avg'],
    'spo2_epochs': ['date', 'timestamp', 'time_str', 'spo2_value', 'sleep_stage'],
    'hourly_spo2': ['date', 'hour', 'spo2_avg', 'spo2_min', 'drops_below_90'],
    'anomaly_alerts': ['date', 'severity', 'message'],
}

class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            q = parse_qs(parsed.query)
            if parsed.path == '/':
                return self._json({'service': 'health-api', 'db': 'postgres', 'tables': list(ALLOWED)})
            if parsed.path == '/latest':
                with db._conn() as c:
                    cur = c.execute('SELECT * FROM daily_metrics ORDER BY date DESC LIMIT 1')
                    row = cur.fetchone()
                    cols = [d[0] for d in cur.description]
                return self._json(dict(zip(cols, row)) if row else {})
            table = parsed.path.lstrip('/').split('.')[0]
            if table not in ALLOWED:
                return self._json({'error': f'unknown table: {table}'}, 404)
            limit = min(int(q.get('limit', ['100'])[0]), 1000)
            where, params = [], []
            for col in ('date',):
                if col in q:
                    where.append(f'{col} = %s')
                    params.append(q[col][0])
            if 'from' in q:
                where.append('date >= %s'); params.append(q['from'][0])
            if 'to' in q:
                where.append('date <= %s'); params.append(q['to'][0])
            sql = f'SELECT {", ".join(ALLOWED[table])} FROM {table}'
            if where:
                sql += ' WHERE ' + ' AND '.join(where)
            sql += f' ORDER BY date DESC LIMIT {limit}'
            with db._conn() as c:
                cur = c.execute(sql, params)
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
            return self._json([dict(zip(cols, r)) for r in rows])
        except Exception as e:
            return self._json({'error': str(e)}, 500)

    def log_message(self, *a):
        pass

ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
