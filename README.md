# DNS Over HTTPS Proxy

Python scripts that supports proxying DNS over HTTPS [draft-ietf-doh-dns-over-https](https://tools.ietf.org/html/draft-ietf-doh-dns-over-https-02) to a recursive resolver.

The project comes with 3 commands:
* doh-client: A tool to perform a DNS query against DOH server.
* doh-proxy: A service that receives DOH queries and forwards them to a recursive resolver.
* doh-stub: A service that listens for DNS queries and forwards them to a DOH server.

See the CONTRIBUTING file for how to help out.

DOH Proxy was created during [IETF Hackathon 100](https://www.ietf.org/hackathon/100-hackathon.html) as a proof-of-concept and is not used at Facebook.

You are welcome to use it, but be aware that support is limited and best-effort.

## Requirements

* python >= 3.5
* h2
* aioh2
* dnspython

## Building

DOH Proxy uses Python'setuptools to manage dependencies and build.

To install its dependencies:

```
python setup.py develop
```

To build:
```
python setup.py build
```

## Installing

```
python setup.py install
```

## Usage

### Proxy

```
$ sudo doh-proxy \
    --upstream-resolver=::1 \
    --certfile=./fullchain.pem \
    --keyfile=./privkey.pem
```


### Stub resolver


You can start a stub resolver and query it. The traffic will be forwarded to a remote DOH server.

```
$ doh-stub \
    --listen-port 5553 \
    --domain foo.bar \
    --remote-address ::1
```

### Test Client

```
$ doh-client  \
    --domain dns.dnsoverhttps.net \
    --qname sigfail.verteiltesysteme.net \
    --dnssec
id 37762
opcode QUERY
rcode SERVFAIL
flags QR RD RA
edns 0
eflags DO
payload 4096
;QUESTION
sigfail.verteiltesysteme.net. IN AAAA
;ANSWER
;AUTHORITY
;ADDITIONAL

$ doh-client  \
    --domain dns.dnsoverhttps.net \
    --qname sigok.verteiltesysteme.net \
    --dnssec
id 49772
opcode QUERY
rcode NOERROR
flags QR RD RA AD
edns 0
eflags DO
payload 4096
;QUESTION
sigok.verteiltesysteme.net. IN AAAA
;ANSWER
sigok.verteiltesysteme.net. 60 IN AAAA 2001:638:501:8efc::139
sigok.verteiltesysteme.net. 60 IN RRSIG AAAA 5 3 60 20180130030002 20171031030002 30665 verteiltesysteme.net. O7QgNZFBu3fULvBXwM39apv5nMehh51f mLOVEsC8qZUyxIbxo4eDLQt0JvPoPpFH 5TbWdlm/jxq5x2/Kjw7yUdpohhiNmdoD Op7Y+RyHbf676FoC5Zko9uOAB7Pp8ERz qiT0QPt1ec12bM0XKQigfp+2Hy9wUuSN QmAzXS2s75k=
;AUTHORITY
;ADDITIONAL
```

## Development

From within the root of the repository, you can test the proxy, stub and client respectively
by using the following commands:

```
$ sudo PYTHONPATH=. python3 ./dohproxy/proxy.py ...
```

```
$ PYTHONPATH=. python3 ./dohproxy/stub.py ...
```

```
$ PYTHONPATH=. python3 ./dohproxy/client.py ...
```

## License
DOH Proxy is BSD-licensed.
