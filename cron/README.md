# Cron

## Debugging

Cron jobs automatically will be running in `api` container due to their schedule.

Cron doesn't write logs by default, so if tasks wouldn't complete or fall with the error, you don't see it.

But it is possible to write logs in special file, just add to `cron.txt` file for your script such expression:
```
>> /var/log/cron.log 2>&1
```

For example:
```
* * * * * PYTHONPATH=/app python /app/cron/inactivate_products_task.py >> /var/log/cron.log 2>&1
```

After that in `sh` of api container restart cron and read the logs:

```
docker exec -it prozorro-catalog_api_1 sh
/app # crond -b
/app # tail -f /var/log/cron.log
```

## Tasks

To check whether all your tasks are seen in crontab file:

```
crontab -l
```

## EOF

Don't forget that `cron.txt` file should always have empty line in the end of file!!!