docker-compose -p plant -f docker/plant/docker-compose.plant.yml up -d --build
docker-compose -p hq -f docker/hq/docker-compose.hq.yml up -d --build


# docker-compose -p plant -f docker/plant/docker-compose.plant.yml up -d
# docker-compose -p hq -f docker/hq/docker-compose.hq.yml up -d 