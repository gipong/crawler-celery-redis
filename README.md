# Crawler application, Celery and Redis with docker-compose

Dockerize crawler application, Celery and Redis with docker-compose

### Build & Launch

```bash
docker-compose up -d --build
```

Flask application's endpoints on port `5001`, the code in [api/app.py](api/app.py) is for endpoints

To shut down all container:
```bash
docker-compose down
```

All of tasks is defined in [queue/tasks.py](celery-queue/tasks.py) 

### Scale up worker

To add more workers:
```bash
docker-compose up -d --scale worker=5 --no-recreate
```

[Flower](https://github.com/mher/flower) server for monitoring workers on port `5555`


### Dispatch the fetch task to worker

To tar a folder with your base images
```bash
curl -X POST -F 'tar=@demo.tar" http://localhost:5001/fetch/<task_name>
```






