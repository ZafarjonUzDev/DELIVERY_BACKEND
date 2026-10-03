FROM nginx:alpine

# Nginx sozlamalarini nusxalash
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Barcha frontend fayllarini Nginx papkasiga o'tkazish
COPY . /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]