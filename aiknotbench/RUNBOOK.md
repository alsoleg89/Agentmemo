# aiknotbench runbook

## Предпочтительный способ запуска

Запускать из корня `ai-knot/` с инлайн `AI_KNOT_COMMAND` — не нужен `export` всего `.env`:

```bash
cd /Users/alsoleg/Documents/github/ai-knot
AI_KNOT_COMMAND=.venv/bin/ai-knot-mcp npx tsx aiknotbench/src/index.ts run -r <run-id>-conv0 --top-k 60 --limit 1
```

Или из `aiknotbench/` с относительным путём:

```bash
cd aiknotbench
AI_KNOT_COMMAND=../.venv/bin/ai-knot-mcp npx tsx src/index.ts run -r <run-id>-conv0 --top-k 60 --limit 1
```

## Запуск 10 параллельных conv

```bash
cd /Users/alsoleg/Documents/github/ai-knot/aiknotbench
export $(grep -v '^#' .env | xargs)

for c in 0 1 2 3 4 5 6 7 8 9; do
  npx tsx src/index.ts run -r <run-id>-conv${c} --convs ${c} --top-k 60 > /tmp/<run-id>-conv${c}.log 2>&1 &
  echo "started conv${c} (PID $!)"
done
```

Каждый conv — отдельный run-id (`pf4-conv0`, `pf4-conv1`, ...) и отдельный SQLite файл.

## Монитор (авто-перезапуск упавших)

```bash
cat > /tmp/<run-id>-monitor.sh << 'EOF'
#!/bin/bash
cd /Users/alsoleg/Documents/github/ai-knot/aiknotbench
export $(grep -v '^#' .env | xargs) 2>/dev/null

while true; do
  for c in 0 1 2 3 4 5 6 7 8 9; do
    runid="<run-id>-conv${c}"
    logf="/tmp/<run-id>-conv${c}.log"
    if pgrep -f "index.ts run -r ${runid}" > /dev/null 2>&1; then continue; fi
    if [ -f "data/runs/${runid}/report.json" ]; then continue; fi
    echo "[$(date)] Restarting ${runid}..." >> /tmp/<run-id>-monitor.log
    npx tsx src/index.ts run -r ${runid} --convs ${c} --top-k 60 >> ${logf} 2>&1 &
  done
  sleep 30
done
EOF
chmod +x /tmp/<run-id>-monitor.sh
nohup /tmp/<run-id>-monitor.sh >> /tmp/<run-id>-monitor.log 2>&1 &
```

## Стоп всего

```bash
pkill -f "<run-id>-conv"
pkill -f "<run-id>-monitor"
```

## Статус таблицы (10 conv)

```bash
for c in 0 1 2 3 4 5 6 7 8 9; do
  runid="<run-id>-conv${c}"
  cp_file="data/runs/${runid}/checkpoint.json"
  report_file="data/runs/${runid}/report.json"
  if [ -f "$report_file" ]; then
    python3 -c "
import json
r=json.load(open('$report_file'))
bt=r.get('byType',{})
def s(k): t=bt.get(str(k),{}); return f\"{t.get('correct',0)}/{t.get('total',0)}\"
c14=r.get('categories1to4',{})
print(f\"DONE|{s(1)}|{s(2)}|{s(3)}|{s(4)}|{s(5)}|{c14.get('correct',0)}/{c14.get('total',0)}\")"
  elif [ -f "$cp_file" ]; then
    python3 -c "
import json
cp=json.load(open('$cp_file'))
results=cp.get('results',[])
from collections import defaultdict
cats=defaultdict(lambda:[0,0])
for r in results:
  cats[r['category']][1]+=1
  if r['verdict']=='CORRECT': cats[r['category']][0]+=1
def s(k): return f\"{cats[k][0]}/{cats[k][1]}\"
c14=[r for r in results if 1<=r['category']<=4]
c14c=sum(1 for r in c14 if r['verdict']=='CORRECT')
print(f\"RUN|{s(1)}|{s(2)}|{s(3)}|{s(4)}|{s(5)}|{c14c}/{len(c14)}\")"
  else
    echo "MISSING"
  fi
done
```

## Диагностика качества recall

```bash
# Смотреть context который возвращает query_json:
cat data/runs/<run-id>-conv0/log.jsonl | python3 -c "
import json, sys
for l in sys.stdin:
  d = json.loads(l)
  print('Q:', d['question'][:60])
  print('CTX:', d['context'][:200])
  print('V:', d['verdict'])
  print()
" | head -60
```

```bash
# Смотреть atomic_claims в SQLite:
python3 -c "
import sqlite3
con = sqlite3.connect('data/runs/<run-id>-conv0/knot.db')
cur = con.cursor()
cur.execute('SELECT COUNT(*) FROM raw_episodes'); print('raw_episodes:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM atomic_claims'); print('atomic_claims:', cur.fetchone()[0])
cur.execute('SELECT kind, subject, relation, value_text FROM atomic_claims LIMIT 20')
for r in cur.fetchall(): print(' ', r)
"
```

## Логи

| Что | Где |
|-----|-----|
| stdout/stderr tsx процесса | `/tmp/<run-id>-conv{N}.log` |
| QA детали (question/context/answer/verdict) | `data/runs/<run-id>-conv{N}/log.jsonl` |
| Прогресс / чекпоинт | `data/runs/<run-id>-conv{N}/checkpoint.json` |
| Финальный отчёт | `data/runs/<run-id>-conv{N}/report.json` |
| SQLite база | `data/runs/<run-id>-conv{N}/knot.db` |
| Монитор лог | `/tmp/<run-id>-monitor.log` |

## Переменные окружения (aiknotbench/.env)

```
AI_KNOT_COMMAND=/Users/alsoleg/Documents/github/ai-knot/.venv/bin/ai-knot-mcp
AI_KNOT_PROVIDER=openai
AI_KNOT_LLM_RECALL=false
AI_KNOT_EMBED_URL=https://api.openai.com
AI_KNOT_EMBED_MODEL=text-embedding-3-small
DEFAULT_ANSWER_MODEL=gpt-4o-mini
DEFAULT_JUDGE_MODEL=gpt-4o-mini
```

## Известные проблемы

- **session_date формат**: LoCoMo даты `"8 May, 2023"` не ISO — фикс в `aiknot.ts` (конвертация через `new Date()`) и `_mcp_tools.py` (fallback внутри try/except).
- **DDSA**: `AIKNOT_DDSA_ENABLED=false` даёт +8pp cat1, +3pp cat2 — лучше отключать.
- **pf4 деградация**: новая сборка (v0.9.5) материализует мусорные триплеты (`"Nice to", "meet"`), retrieval ломается. Baseline pf3 = 65.9% cat1-4.
