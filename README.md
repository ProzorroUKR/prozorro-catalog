# Catalog API

## Setup (docker)

### Run application
```
docker-compose up mongo api
```

### For testing
Run all tests
```
docker-compose up tests
```
To run specific tests:
Open console in running container 
```
docker-compose exec tests /bin/sh
python -m unittest test_module1 test_module2
python -m unittest test_module.TestClass
python -m unittest test_module.TestClass.test_method
```

## Setup (local)

### Run application
```
python -m catalog.api
```
or
```
gunicorn catalog.api:application --bind 0.0.0.0:8000 --worker-class aiohttp.GunicornWebWorker
```
