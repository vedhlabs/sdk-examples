# Five functions, three execution experiences

This is the runnable companion to the canonical docs repository's Inside Aga
walkthrough. [The complete module](../src/quickstart/inside_execution.py) contains
one App, five simulated KYC providers, and sticky/distributed Workflow definitions.
No external account or real identity data is needed. Each provider sleeps for
1.2 seconds inside its Step and returns a synthetic result with diagnostic timing.

Set up the released server and virtual environment using
[your first workflow](first-workflow.md). In two terminals, from `sdk-examples`:

```bash
# Terminal one: leave this worker running.
source .venv/bin/activate
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=inside-lab
python -m quickstart.inside_execution --worker
```

```bash
# Terminal two: use the same server and scope.
source .venv/bin/activate
export AGA_URL=http://127.0.0.1:8080
export AGA_NAMESPACE=inside-lab
python -m quickstart.inside_execution --mode sync
python -m quickstart.inside_execution --mode sync --parallel
python -m quickstart.inside_execution --mode async
python -m quickstart.inside_execution --mode async --parallel
python -m quickstart.inside_execution --mode async-distributed
python -m quickstart.inside_execution --mode async-distributed --parallel
```

Let each Run finish before submitting the next for an isolated comparison.
Sync waits and prints the final five results. Async modes return after admission;
add `--wait` to observe their results in the terminal. `--parallel` calls all five
Steps before `app.join`; without it, each call is awaited before the next.

Open [the dashboard](http://127.0.0.1:8080), choose **default / inside-lab**, and
find the printed Run ID. Select a Step to see its input and output. Optional
`--applicant-id DEMO-002` tags the root with an `applicant` resource; search
`resource:applicant/DEMO-002`. Optional `--run-id` must be fresh for a new experiment.

Capacity is not a start barrier. Distributed tasks are separately claimed and
may start at different times; extremely short functions can finish between
claims. Sticky work runs in a bounded local pool. Both support overlapping work.
Monotonic `started_ns`/`finished_ns` values are only comparable within this
single-process lab, not across hosts. These are observations, not a benchmark.

The module is also tested without a server:

```bash
python -m pytest tests/test_inside_execution.py -q
```

For database rows, locks, and replay identity, read
`docs/inside-aga/14b-run-the-five-step-lab.md` in the sibling canonical docs repo.
Its rendered route is `/aga/inside/14b-run-the-five-step-lab`; the public blog
does not host Inside Aga. Stop only this example's worker with Ctrl-C when done.
