#!/usr/bin/env bash

# deployment script to run on server for buzzword swisslaw

# Run it like this to get the container ID:

#     ID=$(./configs/swiss-law-deploy.sh)
echo "MAKE SURE YOU PASSED IN PASSWORD: ${@: -1}"

PASSWORD="${@: -1}"

# ensure db file is there
touch db.sqlite3
sudo chown www-data:www-data db.sqlite3
sudo chmod 777 db.sqlite3

# get latest repo
git checkout swisslaw
git pull

# build the image (note, data is still missing)
DJANGO_SUPERUSER_PASSWORD="${@: -1}"
sudo docker build - < Dockerfile --build-arg DJANGO_SUPERUSER_PASSWORD=$PASSWORD --no-cache -t buzzword:swisslaw

# now kill the old container if running
# sudo docker container kill $(docker ps -q)
touch db.sqlite3

# add settings, db and data in as volume
ID=$(sudo docker run -itd -p 80:8000 \
    --mount type=bind,source="$(pwd)"/buzzword/settings.py,target=/buzzword/buzzword/settings.py \
    --mount type=bind,source="$(pwd)"/db.sqlite3,target=/buzzword/db.sqlite3 \
    --mount type=bind,source="$(pwd)"/static/corpora,target=/buzzword/static/corpora \
    buzzword:swisslaw 2>&1)

# all the commands we need to do to get configured
sudo docker exec -it $ID python manage.py migrate
sudo docker exec -it $ID python manage.py load_languages
sudo docker exec -it $ID python manage.py load_corpora
sudo docker exec -it $ID python manage.py do_ocr
echo "Creating superusers with password: $PASSWORD"
sudo docker exec -it $ID python manage.py createsuperuser --noinput --username danny --email danny@testing.com
sudo docker exec -it $ID python manage.py createsuperuser --noinput --username martin.kurz --email martin@testing.com

echo "$ID"
