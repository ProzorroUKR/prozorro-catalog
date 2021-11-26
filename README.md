# Catalog API
## Setup
### Run application
```
docker-compose up mongo api
```
### Stop application
```
docker-compose stop
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
