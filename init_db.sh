#!/bin/bash

# The result of this script will be a folder $DB_VOL ready to be used as a mysql volume for mariadb with the schema initialized.
# If an argument is provided, it will be treated as a backup sql script.

VENV="/tmp/venv"
VOL="/tmp/vol"
DB_VOL="$VOL/db"
DB_PASS="root"
DB_PORT="3306"

mkdir $VOL
docker run --name db_init --rm -d -p $DB_PORT:3306 -e MYSQL_ROOT_PASSWORD=$DB_PASS -v $VOL:$VOL -v $DB_VOL:/var/lib/mysql  mariadb

python -m venv $VENV
. $VENV/bin/activate
pip install -r requirements.txt

docker exec db_init bash -c "echo 'create database leagues' | mysql -uroot -p$DB_PASS"
echo -e "from champions_leagues import db\ndb.create_all()" | python

db_backup=$1

if [ -f "$db_backup" ]; then

    cp $db_backup "$VOL/db_backup.sql"
    docker exec -it db_init bash -c "cat $VOL/db_backup.sql | mysql -uroot -p$DB_PASS leagues"

fi

docker container stop db_init
rm -rf $VENV
