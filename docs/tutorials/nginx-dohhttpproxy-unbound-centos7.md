---
layout: default
---

# DNS over HTTPS with NGINX/DOH-PROXY/Unbound on CentOS7

This tutorial will cover installing a working `doh-proxy` setup fronted by [NGINX](http://nginx.org/).

We assume that we are setting up a DoH server for the domain `dns.example.com` and that the A/AAAA DNS records are already set to point to the server that is going to be configured.


Port 443 is also assumed to be opened.

## Setting up the environment


### Basic tooling

Let's get this out of our way first... and install some packages that will be needed during this tutorial:

```bash
yum -y install git bind-utils certbot-nginx
```

`git` will be used to be able to install `doh-proxy` directly from the github repository.

`bind-utils` installs `dig` which we will use to perform dns queries.

`certbot-nginx` will be used to get and install a digital certificate from [let's encrypt](https://letsencrypt.org/).

### Python3.6
To run `doh-proxy` we need at least python3.5 installed. We are going to use the python packages provided by [IUS Community Project](https://ius.io/) to get a working `python3.6` set up in no time.

```bash
yum -y install https://centos7.iuscommunity.org/ius-release.rpm
yum -y install python36u python36u-pip python36u-devel
```

## Setting up doh-proxy

### Installing doh-proxy

`doh-proxy` is being packaged and uploaded to [pypi](https://pypi.python.org/pypi/doh-proxy), so 1 simple method to install it is to run:

```bash
pip3.6 install doh-proxy
```

If you like living on the edge, you can install from master using:

```bash
pip3.6 install git+https://github.com/facebookexperimental/doh-proxy.git
```

### Create a dedicated user

`doh-proxy` will be running as its own user, but we need to create it first.

```bash
adduser -r doh-proxy \
    -d /var/lib/doh-proxy \
    -c 'DOH Proxy server' \
    -s /sbin/nologin \
    -U
mkdir /var/lib/doh-proxy \
    && chown doh-proxy: /var/lib/doh-proxy \
    && chown 700 /var/lib/doh-proxy
```


### Create a doh-proxy unit file

The `systemd` unit files will ensure that `doh-proxy` is started upon bootup.

```bash
cat <<EOF > /etc/systemd/system/doh-httpproxy\@.service
[Unit]
Description=DOH HTTP Proxy on %I
After=syslog.target network.target
Before=nginx.target

[Service]
Type=simple
ExecStart=/bin/doh-httpproxy --upstream-resolver ::1 --level DEBUG --listen-address=::1 --port %I
Restart=always
User=doh-proxy
Group=doh-proxy

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
```


Now, we will set up `systemd` to start 2 `doh-httpproxy` processes, one on port 8080 and one on port 8081
and start them.

```bash
for i in 8080 8081
do
    # We can't link on CentOS7 due to https://github.com/systemd/systemd/issues/3010
    # ln -s /etc/systemd/system/doh-httpproxy\@.service \
    cp /etc/systemd/system/doh-httpproxy\@.service \
        /etc/systemd/system/doh-httpproxy\@${i}.service
    systemctl enable doh-httpproxy@${i}
    systemctl start doh-httpproxy@${i}
done
```

That should be it for `doh-proxy`.... but we need a recursive nameserver to perform the actual DNS queries
and all the recursion logic. In this example we will be using [unbound](https://www.unbound.net/).

## Setting unbound

Setting an instance of `unbound` that listen on `127.0.0.1` and `::1` is pretty straightforward.

Basically, we just need to install the package, enable it and start it.

```bash
yum -y install unbound
systemctl enable unbound
systemctl start unbound
```

You can confirm that it works by running:
```bash
dig @::1 example.com
```
and getting an `A` record.

Finally now, we are left with the last bit, which is to configure `NGINX` with HTTP2 and that uses our doh-proxy backends.

## Setting nginx

First, we need to install `NGINX`:

```bash
yum -y install nginx
systemctl enable nginx
systemctl start nginx
```

Now that we have `NGINX` running, we can use `certbot-nginx` to get a certificate from `let's encrypt`.

```bash
certbot --nginx -d dns.example.com
```

At this stage, we have a working HTTPS server. If you were going to open `https://dns.example.com`, you would get the default `NGINX` page.

We now need to:
* configure HTTP2
* configure NGINX to use our `doh-proxy` backends.


### Configure NGINX

First, we will enable `HTTP2` and tell NGINX to use our `dohproxy` backends.

Open `/etc/nginx/nginx.conf` and look for the lines:
```
    listen [::]:443 ssl ipv6only=on; # managed by Certbot
    listen 443 ssl; # managed by Certbot

```

and replace them with:

```
    listen [::]:443 ssl http2 ipv6only=on; # managed by Certbot
    listen 443 ssl http2; # managed by Certbot
```

We will configure `nginx` to only let `HEAD`, `GET` and `POST` requests to go
through:

```
if ( $request_method !~ ^(GET|POST|HEAD)$ ) {
        return 501;
}
```
Now, we will configure anything that gets to `/dns-query` to be forwarded to our backends:

Find the block:
```
       location / {
       }
```

and replace it with:

```
        location /dns-query {
              proxy_set_header Host $http_host;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_redirect off;
              proxy_buffering off;
              proxy_pass http://dohproxy_backend;
        }
```

Finally, we need to configure our `doh-proxy` backends. Add:

```
upstream dohproxy_backend {
        server [::1]:8080;
        server [::1]:8081;
}
```

right before the block:

```
   server {
   server_name dns.example.com; # managed by Certbot

```

At this stage, you just need to restart NGINX:

```bash
systemctl restart nginx
```
and you should be good to go.... unless you use `SELinux`, in which case a quick solution will be:

```bash
setsebool -P httpd_can_network_connect=true
```

in order to allow NGINX to connect to our proxies.


## Testing

You can use `doh-stub` to test that everything is working fine. From the server you are configuring `doh-proxy` on, in one terminal run:

```bash
doh-stub --listen-port 5353 --domain dns.example.com --remote-address ::1
```

This will spin up a `doh-stub` that will listen on port 5353 and connect to our new `doh-proxy` on IP `::1`.

You can now query DNS on the doh server using:

```bash
dig @::1 -p 5353 example.com
```

and this should show the `A` record of example.com.

At this stage, you should have a working end to end NGINX/doh-proxy/unbound setup.


Now, all you have to do is to configure an application to use your `doh-proxy` or set your whole system to use DoH by running [the client doh-stub](simple-setup.md#running-the-client-stub)
