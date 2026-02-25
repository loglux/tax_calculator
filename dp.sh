#!/bin/sh

# Stop script execution on error
set -e

# Image and container name
NAME="tax_calculator"
PORT=9000
CREATE_LOCAL_ADMIN_IF_MISSING="${CREATE_LOCAL_ADMIN_IF_MISSING:-1}"
LOCAL_ADMIN_USERNAME="${LOCAL_ADMIN_USERNAME:-admin}"
LOCAL_ADMIN_PASSWORD="${LOCAL_ADMIN_PASSWORD:-admin12345}"
LOCAL_ADMIN_EMAIL="${LOCAL_ADMIN_EMAIL:-admin@example.com}"

# Build Docker image
echo "Building Docker image..."
docker build -t $NAME .

# Check if the container is running or exists
if [ "$(docker ps -a -q -f name=$NAME)" ]; then
    echo "Stopping and removing existing container..."
    docker stop $NAME
    docker rm $NAME
fi

# Run new container on the fixed port
echo "Running new container on port $PORT..."
docker run -d --name $NAME -p $PORT:8000 \
    -e DJANGO_SETTINGS_MODULE=tax_calculator.settings_docker \
    $NAME

# Check if the container started successfully
if [ "$(docker ps -q -f name=$NAME)" ]; then
    echo "Running database migrations..."
    docker exec $NAME python manage.py migrate --noinput

    echo "Syncing tax rates..."
    docker exec $NAME python manage.py sync_tax_rates

    if [ "$CREATE_LOCAL_ADMIN_IF_MISSING" = "1" ]; then
        echo "Ensuring local admin exists (create-if-missing)..."
        docker exec \
            -e DJANGO_SUPERUSER_USERNAME="$LOCAL_ADMIN_USERNAME" \
            -e DJANGO_SUPERUSER_PASSWORD="$LOCAL_ADMIN_PASSWORD" \
            -e DJANGO_SUPERUSER_EMAIL="$LOCAL_ADMIN_EMAIL" \
            $NAME sh -lc "python manage.py shell -c \"from django.contrib.auth import get_user_model; import os; U=get_user_model(); username=os.environ['DJANGO_SUPERUSER_USERNAME']; password=os.environ['DJANGO_SUPERUSER_PASSWORD']; email=os.environ['DJANGO_SUPERUSER_EMAIL']; u, created = U.objects.get_or_create(username=username, defaults={'email': email, 'is_staff': True, 'is_superuser': True}); created and (u.set_password(password) or True) and (u.save() or True); print('local admin created' if created else 'local admin already exists')\""
    fi

    echo "Deployment completed successfully. Access the application on port $PORT."
else
    echo "Failed to start container. Here are the logs:"
    docker logs $NAME
    docker rm $NAME
fi
