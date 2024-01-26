# metrics-python

> Generic set of metrics for Python applications.

We collect metrics utils in this package to hopefully make a generic package we
can use in other projects in the future.

## Labels

Common labels like app, env, cluster, component, role, etc. is added to the
metrics using the scrape config. Adding these metrics is not a responsibility we
have in the metrics-python package.

## Application info

Some properties from the application is not added as metric labels by default by
the scrape config. One example is the application version. metrics-python has a
util to expose labels like this to Prometheus.

```python
from metrics_python.generics.info import expose_application_info

expose_application_info(version="your-application-version")
```

## Django

### Query count and duration in views

Database query count, duration, and duplicate queries can be observed
by adding the `QueryCountMiddleware`. Add the middleware as early as
possible in the list of middlewares to observe queries executed by
other middlewares.

```python
MIDDLEWARE = [
    ...
    "metrics_python.django.QueryCountMiddleware",
]
```

## Celery

To setup Celery monitoring, import and execute `setup_celery_metrics` as early
as possible in your application to connect Celery signals. This is usually done
in the `settings.py` file in Django applications.

```python
from metrics_python.celery import setup_celery_metrics

setup_celery_metrics()
```

## django-api-decorator

To measure request durations to views served by django-api-decorator, add the `DjangoAPIDecoratorMetricsMiddleware`.

```python
MIDDLEWARE = [
    ...
    "metrics_python.django_api_decorator.DjangoAPIDecoratorMetricsMiddleware",
]
```

## GraphQL

### Strawberry

The Prometheus extension needs to be added to the schema to instrument GraphQL
operations.

```python
import strawberry
from metrics_python.graphql.strawberry import PrometheusExtension

schema = strawberry.Schema(
    Query,
    extensions=[
        PrometheusExtension,
    ],
)
```

### Graphene

metrics-python has a Graphene middleware to instrument GraphQL operations. Add
the middleware to Graphene by changing the GRAPHENE config in `settings.py`.

```python
GRAPHENE = {
    ...
    "MIDDLEWARE": ["metrics_python.graphql.graphene.MetricsMiddleware"],
}
```

## Gunicorn

To setup Gunicorn monitoring, add the Prometheus logger (to measure request
durations) and add the worker state signals to the gunicorn config.

```python
from metrics_python.generics.workers import export_worker_busy_state

logger_class = "metrics_python.gunicorn.Prometheus"

def pre_request(worker: Any, req: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=True)


def post_request(worker: Any, req: Any, environ: Any, resp: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=False)


def post_fork(server: Any, worker: Any) -> None:
    export_worker_busy_state(worker_type="gunicorn", busy=False)
```

## Releasing new versions

1. Create PRs for the features you want to have in the new release, and get them
   reviewed, approved and merged into the `main` branch. Don't change version
   numbers in these feature PRs.

2. Create a new PR incrementing the version of project in
   [pyproject.toml](https://github.com/kolonialno/metrics-python/edit/main/pyproject.toml).
   You need to change the value of the `version` field in the `[tool.poetry]`
   section.

   We follow [semantic versioning](https://semver.org/) using a
   `major.minor.patch` format that convey backwards-compatibility. If your
   change is backwards-compatible, increment the patch version by one.
   Otherwise, increment the minor version by one.

3. Tag the release.

   There are multiple ways to tag a release. We recommend using the Github UI as
   this makes it easy to create a release with a well-written and well-formatted
   change log. After bumping the package version you navigate to the
   [new release page](https://github.com/kolonialno/metrics-python/releases/new). Fill in
   the correct tag version and release title. If you for example were to bump
   `metrics-python` to `0.1.0` you would fill in

   - Tag version: `metrics-python/v0.1.0`
   - Release title: `metrics-python v0.1.0`

   Make sure to match the tag name pattern `metrics-python/v*`, so that you trigger
   release of the correct project. The change log should be a succinct
   description of the changes since the last release. If you are unsure how to
   write a good change log you can consult the
   [release list](https://github.com/kolonialno/metrics-python/releases) for inspiration.

4. GitHub Actions will build the release and upload it to
   [GemFury](https://manage.fury.io/dashboard/oda).
