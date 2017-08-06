# Cloning the project

1. `sudo apt install python3-venv`
1. `python3 -m venv venv-global-server`
1. `source venv-global-server/bin/activate`
1. `pip install -r requirements.txt`

# Running the tests

`pytest`

# Running the server

1. `python3 manage.py makemigrations app_name_app` (if the models were changed)
1. `python3 manage.py sqlmigrate app_name_app 0001`
1. `python3 manage.py migrate`
1. `python3 manage.py runserver 8080`

# Updating the requirements file

`pip freeze > requirements.txt`
