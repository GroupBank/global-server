# Cloning the project

pip freeze > requirements.txt

sudo apt install python3-venv
python3 -m venv VENV-group-server
source VENV-group-server/bin/activate
pip install -r requirements.txt
python manage.py runserver 8080

# Running the server

0. `python3 manage.py makemigrations main_server_app` (if the models were changed)
1. `python3 manage.py sqlmigrate main_server_app 0001`
2. `python3 manage.py migrate`
3. `python3 manage.py runserver`

