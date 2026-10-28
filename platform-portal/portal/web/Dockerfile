FROM marquezproject/marquez-web:0.51.1@sha256:7312112ca0e611b0a37b00d3da6a677485ae4a97622b23d3ae24d849a927868b
WORKDIR /usr/src/app
COPY public-readonly.js public-readonly.css public-datasets.js public-datasets.css ./dist/
COPY install-overlay.cjs /tmp/install-overlay.cjs
RUN node /tmp/install-overlay.cjs && rm /tmp/install-overlay.cjs
EXPOSE 3000
