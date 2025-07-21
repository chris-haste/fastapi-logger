# Quickstart Tutorial: Fapilog End-to-End

## Introduction

A hands-on, step-by-step guide to get you from data ingestion to analysis and dashboarding with Fapilog.

## Prerequisites

- Python 3.8+
- FastAPI
- Fapilog installed ([see Installation](user-guide.md#installation))

---

## Step 1: Ingestion

In this step, you'll set up a basic FastAPI app and configure Fapilog to ingest log events.

```python
from fastapi import FastAPI
import fapilog

# Initialize Fapilog
fapilog.bootstrap()

app = FastAPI()

@app.get("/")
def read_root():
    fapilog.logger.info("Hello from Fapilog!")
    return {"message": "Log event ingested!"}
```

**Explanation:**

- `fapilog.bootstrap()` sets up the logging pipeline with default settings.
- The FastAPI route logs a message using Fapilog.
- Run the app and visit `/` to generate and ingest a log event.

**See also:** [Primer](primer.md), [User Guide](user-guide.md#logging), [API Reference](api-reference.md)

[Next: Analysis →](#step-2-analysis)

## Step 2: Analysis

Now that you are ingesting logs, let's analyze them. For this example, we'll read logs from a file sink and print out error events.

First, configure Fapilog to write logs to a file (if not already set):

```python
import fapilog

fapilog.bootstrap({
    'sinks': [
        {
            'type': 'file',
            'path': 'logs/app.log',
            'level': 'INFO',
        }
    ]
})
```

**Analyzing logs:**
You can use Python to parse the log file and extract error events:

```python
import json

with open('logs/app.log') as f:
    for line in f:
        log_event = json.loads(line)
        if log_event.get('level') == 'ERROR':
            print(log_event)
```

**Explanation:**

- The first snippet configures Fapilog to write logs to `logs/app.log`.
- The second snippet reads the log file and prints any log event with level `ERROR`.
- You can adapt the analysis code to filter, aggregate, or visualize logs as needed.

**See also:** [API Reference](api-reference.md), [Examples](../examples/), [Config](config.md)

[Previous: Ingestion](#step-1-ingestion) | [Next: Dashboard →](#step-3-dashboard)

## Step 3: Dashboard

Now, let's visualize your log data. We'll use [Streamlit](https://streamlit.io/) for a quick, interactive dashboard.

**Install Streamlit:**

```bash
pip install streamlit
```

**Create a dashboard script (dashboard.py):**

```python
import streamlit as st
import json

st.title('Fapilog Error Dashboard')

log_file = 'logs/app.log'
errors = []

with open(log_file) as f:
    for line in f:
        log_event = json.loads(line)
        if log_event.get('level') == 'ERROR':
            errors.append(log_event)

st.write(f"Total error events: {len(errors)}")

for event in errors:
    st.json(event)
```

**Run the dashboard:**

```bash
streamlit run dashboard.py
```

**Explanation:**

- This script reads your log file and displays error events in a simple web dashboard.
- You can extend it to visualize other log levels, add charts, or filter by fields.
- Streamlit makes it easy to build interactive dashboards with minimal code.

**See also:** [User Guide](user-guide.md#dashboarding), [Examples](../examples/), [Primer](primer.md)

[Previous: Analysis](#step-2-analysis)

---

## Troubleshooting & Common Pitfalls

- **Fapilog not found:** Ensure you have installed Fapilog in your environment (`pip install fapilog`).
- **Log file not created:** Check that the directory for your log file exists (e.g., `logs/`). Create it if missing.
- **Streamlit not installed:** Install with `pip install streamlit`.
- **Streamlit dashboard not updating:** Make sure you are writing logs to the correct file and refresh the dashboard page.
- **JSON decode errors:** Ensure each log event is written as a single line of valid JSON.

---

## Next Steps

- Explore the [User Guide](user-guide.md) for more advanced features and configuration options.
- Review the [API Reference](api-reference.md) for details on Fapilog's classes and functions.
- Try out more [Examples](../examples/) to deepen your understanding.
- Contribute improvements or new tutorials by following the [Style Guide](style-guide.md).

---

## Internal Links

- [Core Concepts](user-guide.md#core-concepts)
- [API Reference](api-reference.md)
- [Examples](../examples/)
