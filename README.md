# WebIndexer

## Docker

Requires Docker.

### build
```
docker build -t webindexer:latest .
```

### run
```
docker run -d -p 5000:5000 webindexer
```

### test
```
docker exec $(docker ps -q -f ancestor=webindexer:latest) python test_database.py
```

### stop
```
docker stop $(docker ps -q -f ancestor=webindexer:latest)
```

## Local

Requires Python 3.10+.

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python test_database.py  # run tests
python app.py  # run app
```
