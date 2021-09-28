# Catalog API
## Setup
### Run application
```
docker-compose up
```
### Stop application
```
docker-compose stop
```
### For testing
Open console in running container ```docker exec -it <container name> /bin/bash```

To run specific tests:
```
python -m unittest test_module1 test_module2
python -m unittest test_module.TestClass
python -m unittest test_module.TestClass.test_method
```
