FROM nginx:1.23

COPY ./conf.d/default.conf /etc/nginx/conf.d/default.conf
COPY ./ssl /etc/nginx/ssl

RUN mkdir -p /app/static /app/media

EXPOSE 80 